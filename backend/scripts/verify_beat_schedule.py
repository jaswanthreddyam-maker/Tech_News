import sys

from celery_app import celery_app


def main():
    print("Verifying Celery Beat Schedule vs Registered Tasks...")

    # Get all registered tasks locally
    registered_tasks = list(celery_app.tasks.keys())

    beat_schedule = celery_app.conf.beat_schedule or {}
    missing_tasks = []

    for job_name, job_config in beat_schedule.items():
        task_name = job_config.get("task")
        if task_name not in registered_tasks:
            missing_tasks.append((job_name, task_name))

    if missing_tasks:
        print("\n[FAILED] Found scheduled tasks that are NOT registered:")
        for job, task in missing_tasks:
            print(f"  - Job: {job} -> Task: {task}")
        sys.exit(1)

    print(f"\n[PASSED] All {len(beat_schedule)} scheduled tasks are registered successfully!")
    sys.exit(0)


if __name__ == "__main__":
    main()
