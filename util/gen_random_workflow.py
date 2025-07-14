import random


def gen_random_workflow(workflow_path: str = ".github/workflows/rating-chart.yml") -> str:
    cron_line = '"0 */{prevNo} * * *"'
    with open(workflow_path) as f:
        wf = f.read()
    randNo = random.randint(1, 8)
    newCron = cron_line.format(prevNo=randNo)
    for prevNum in range(1, 9):
        prevCron = cron_line.format(prevNo=prevNum)
        if prevCron in wf:
            wf = wf.replace(prevCron, newCron)
            break
    return wf.rstrip()
