import random


def gen_random_workflow(workflow_path: str = ".github/workflows/rating-chart.yml") -> str:
    cron_line = '"0 */{prevNo} * * *"'
    with open(workflow_path) as f:
        wf = f.read()
    rand_no = random.randint(1, 8)
    new_cron = cron_line.format(prevNo=rand_no)
    for prev_num in range(1, 9):
        prev_cron = cron_line.format(prevNo=prev_num)
        if prev_cron in wf:
            wf = wf.replace(prev_cron, new_cron)
            break
    return wf.rstrip()
