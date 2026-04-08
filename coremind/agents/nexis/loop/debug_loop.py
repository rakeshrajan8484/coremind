def debug_loop(agent, task):

    for _ in range(5):  # prevent infinite loops
        result = agent.run_code()

        if result.returncode == 0:
            return "success"

        fix = agent.fix_error(result.stderr)
        agent.apply_fix(fix)

    return "failed"