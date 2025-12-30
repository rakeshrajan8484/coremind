from coremind.tools.schemas import Plan

REF_REQUIRES = {
    "get_email_content": "check_gmail_unread",
    "delete_email": "check_gmail_unread",
    "mark_email": "check_gmail_unread",
}

def validate_plan(plan: Plan):
    seen = []

    for step in plan.steps:
        # Rule 1: tool prerequisites
        prereq = REF_REQUIRES.get(step.action)
        if prereq and prereq not in seen:
            raise ValueError(
                f"{step.action} requires {prereq} to appear earlier in the plan"
            )

        # Rule 2: ref usage requires resolver step earlier
        if "ref" in step.args:
            if "check_gmail_unread" not in seen:
                raise ValueError(
                    f"Reference '{step.args['ref']}' used before inbox was listed"
                )

        seen.append(step.action)
