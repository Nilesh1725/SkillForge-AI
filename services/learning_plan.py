"""
Learning plan generation service — creates personalized skill development roadmaps.
"""

from __future__ import annotations

import logging
from typing import Any

from models.schemas import (
    DayScheduleItem,
    LearningPlanResponse,
    LearningResource,
    LearningTopic,
    SkillGap,
    SkillLearningPlan,
)
from utils.llm_client import query_llm_json
from utils.prompts import LEARNING_PLAN_PROMPT

logger = logging.getLogger(__name__)


def _topological_sort(plans: list[SkillLearningPlan]) -> list[SkillLearningPlan]:
    """Sort plans based on prerequisites to ensure logical sequence."""
    graph: dict[str, list[str]] = {p.skill.strip().lower(): [] for p in plans}
    in_degree: dict[str, int] = {p.skill.strip().lower(): 0 for p in plans}
    plan_map: dict[str, SkillLearningPlan] = {p.skill.strip().lower(): p for p in plans}
    
    for p in plans:
        for prereq in getattr(p, "prerequisites", []):
            prereq_lower = prereq.strip().lower()
            skill_lower = p.skill.strip().lower()
            
            matched_key = None
            if prereq_lower in graph:
                matched_key = prereq_lower
            else:
                # Fuzzy fallback
                for k in graph.keys():
                    if prereq_lower in k or k in prereq_lower:
                        matched_key = k
                        break
                        
            if matched_key:
                graph[matched_key].append(skill_lower)
                in_degree[skill_lower] += 1
                
    queue = [skill for skill, deg in in_degree.items() if deg == 0]
    sorted_skills = []
    
    while queue:
        curr = queue.pop(0)
        sorted_skills.append(curr)
        for neighbor in graph[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
                
    # Handle cycles or disconnected components by appending remaining items
    for p in plans:
        skill_lower = p.skill.strip().lower()
        if skill_lower not in sorted_skills:
            sorted_skills.append(skill_lower)
            
    return [plan_map[s] for s in sorted_skills]


def _generate_day_schedule(
    plans: list[SkillLearningPlan], hours_per_day: float, total_days: int
) -> list[DayScheduleItem]:
    """
    Fill each day with max hours_per_day using carry-over logic for topics.
    """
    schedule = []
    current_day = 1
    remaining_hours_today = hours_per_day

    for plan in plans:
        for topic in plan.topics:
            topic_total_hours = sum(r.estimated_hours for r in topic.resources)
            if topic_total_hours <= 0:
                continue

            remaining_topic_hours = topic_total_hours
            while remaining_topic_hours > 0.05:  # Small threshold for float precision
                if current_day > total_days:
                    break

                allocation = min(remaining_topic_hours, remaining_hours_today)
                if allocation > 0:
                    schedule.append(
                        DayScheduleItem(
                            day=current_day,
                            topic=topic.topic,
                            hours=round(allocation, 1),
                        )
                    )
                    remaining_topic_hours -= allocation
                    remaining_hours_today -= allocation

                if remaining_hours_today <= 0.05:
                    current_day += 1
                    remaining_hours_today = hours_per_day

    return schedule


async def generate_learning_plan(
    skill_gaps: list[SkillGap],
    available_hours_per_day: float = 2.0,
    days_per_week: int = 7,
    target_weeks: int = 8,
) -> LearningPlanResponse:
    """
    Generate a personalized learning plan using day-wise hour scheduling.
    """
    logger.info(
        "Generating learning plan for %d skills, %d weeks, %d days/week, %.1f hrs/day",
        len(skill_gaps),
        target_weeks,
        days_per_week,
        available_hours_per_day,
    )

    # Calculate total hours available
    total_days = target_weeks * days_per_week
    total_available_hours = available_hours_per_day * total_days

    # Build prompt context
    gaps_text = "\n".join(
        f"- {g.skill}: score={g.score}/10, priority={g.priority}, "
        f"recommendation={g.recommendation}"
        for g in skill_gaps
    )

    prompt = LEARNING_PLAN_PROMPT.format(
        skill_gaps=gaps_text,
        hours_per_day=available_hours_per_day,
        target_weeks=target_weeks,
    )

    raw_result = await query_llm_json(prompt=prompt, temperature=0.5)

    plans: list[SkillLearningPlan] = []
    summary = ""
    raw_plans = []

    if isinstance(raw_result, dict):
        raw_plans = raw_result.get("plans", [])
        summary = raw_result.get("summary", "")
    elif isinstance(raw_result, list):
        raw_plans = raw_result

    # Temporary structure to hold topics and compute weights before final allocation
    weights_info = []
    total_weight = 0.0
    
    # Priority weighting mapping
    priority_weights = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}

    for rp in raw_plans:
        if not isinstance(rp, dict):
            continue

        skill_name = rp.get("skill", "")
        priority = rp.get("priority", "MEDIUM")
        current_score = float(rp.get("current_score", 0))
        target_score = float(rp.get("target_score", 8.0))
        
        # Gap is minimum 0. If 0, weight becomes 0, so topic gets 0 hours and pruned
        gap = max(0.0, target_score - current_score)
        skill_priority_weight = priority_weights.get(priority.upper(), 2)
        skill_weight = skill_priority_weight * gap

        # Parse topics
        topics: list[LearningTopic] = []
        raw_topics = rp.get("topics", [])

        if not raw_topics:
            raw_topics = [{"topic": f"{skill_name} Fundamentals", "difficulty_weight": 5}]

        for rt in raw_topics:
            if not isinstance(rt, dict):
                continue
                
            difficulty = int(rt.get("difficulty_weight", 5))
            topic_weight = skill_weight * difficulty
            total_weight += topic_weight
            
            resources: list[LearningResource] = []
            for rr in rt.get("resources", []):
                if isinstance(rr, dict):
                    resources.append(
                        LearningResource(
                            title=rr.get("title", "Untitled Resource"),
                            type=rr.get("type", "tutorial"),
                            url=rr.get("url", ""),
                            estimated_hours=0.0,  # Computed below
                        )
                    )

            if not resources:
                resources.append(
                    LearningResource(
                        title=f"{rt.get('topic', 'General')} Study",
                        type="practice",
                        url="",
                        estimated_hours=0.0,
                    )
                )

            topic_obj = LearningTopic(
                topic=rt.get("topic", f"{skill_name} Concept"),
                week=0,
                daily_hours=available_hours_per_day,
                difficulty_weight=difficulty,
                resources=resources,
                milestones=rt.get("milestones", []),
            )
            topics.append(topic_obj)
            
            # Store info to allocate later
            weights_info.append({
                "topic": topic_obj,
                "weight": topic_weight
            })

        plans.append(
            SkillLearningPlan(
                skill=skill_name,
                covers_skills=rp.get("covers_skills", []),
                priority=priority,
                current_score=current_score,
                target_score=target_score,
                duration_weeks=0,
                topics=topics,
                adjacent_skills=rp.get("adjacent_skills", []),
                prerequisites=rp.get("prerequisites", []),
            )
        )
        
    # Distribute total_available_hours proportionally based on weights
    # Also prune topics with 0 or < 0.5 hours
    for info in weights_info:
        topic_obj = info["topic"]
        topic_weight = info["weight"]
        
        if total_weight > 0:
            topic_hours = total_available_hours * (topic_weight / total_weight)
        else:
            topic_hours = 0.0
            
        if topic_hours < 0.5:
            topic_hours = 0.0
            
        # Distribute equally among resources
        if topic_hours > 0 and topic_obj.resources:
            hours_per_res = topic_hours / len(topic_obj.resources)
            for res in topic_obj.resources:
                res.estimated_hours = round(hours_per_res, 1)
        else:
            for res in topic_obj.resources:
                res.estimated_hours = 0.0

    # Prune 0-hour topics and empty plans
    pruned_plans = []
    for plan in plans:
        valid_topics = []
        for t in plan.topics:
            if sum(r.estimated_hours for r in t.resources) > 0:
                valid_topics.append(t)
                
        if valid_topics:
            plan.topics = valid_topics
            pruned_plans.append(plan)

    plans = pruned_plans

    # Sort plans topologically based on prerequisites
    plans = _topological_sort(plans)

    # Generate the day-wise schedule
    day_schedule = _generate_day_schedule(plans, available_hours_per_day, total_days)
    logger.info("Day-wise schedule generated: %d items", len(day_schedule))

    return LearningPlanResponse(
        total_duration_weeks=target_weeks,
        daily_hours=available_hours_per_day,
        plans=plans,
        day_schedule=day_schedule,
        summary=summary
        or f"Personalized hour-based roadmap for {len(plans)} skills.",
    )