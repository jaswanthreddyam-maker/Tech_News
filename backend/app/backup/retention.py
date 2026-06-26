import datetime


def parse_backup_date(backup_id: str) -> datetime.date | None:
    """Extract date from standard backup_YYYYMMDDTHHMMSSZ_XXXXXX format."""
    parts = backup_id.split("_")
    if len(parts) >= 2 and len(parts[1]) >= 8:
        try:
            return datetime.datetime.strptime(parts[1][:8], "%Y%m%d").date()
        except ValueError:
            pass
    return None


def get_gfs_retention(backup_ids: list[str]) -> tuple[list[str], list[str]]:
    """
    Evaluates GFS (7 daily, 4 weekly, 12 monthly) retention policy on backup list.
    Returns: (list_to_keep, list_to_delete)
    """
    valid_backups = []
    for bid in backup_ids:
        bdate = parse_backup_date(bid)
        if bdate:
            valid_backups.append((bid, bdate))

    # Sort newest first
    valid_backups.sort(key=lambda x: x[1], reverse=True)

    keep_ids = set()

    # 1. Daily: newest backup for each of the last 7 distinct calendar days
    daily_days = {}
    for bid, bdate in valid_backups:
        if bdate not in daily_days:
            daily_days[bdate] = bid
        if len(daily_days) == 7:
            break
    keep_ids.update(daily_days.values())

    # 2. Weekly: newest backup for each of the last 4 distinct calendar weeks (year, ISO_week)
    weekly_weeks = {}
    for bid, bdate in valid_backups:
        year, week_num, _ = bdate.isocalendar()
        week_key = (year, week_num)
        if week_key not in weekly_weeks:
            weekly_weeks[week_key] = bid
        if len(weekly_weeks) == 4:
            break
    keep_ids.update(weekly_weeks.values())

    # 3. Monthly: newest backup for each of the last 12 distinct calendar months (year, month)
    monthly_months = {}
    for bid, bdate in valid_backups:
        month_key = (bdate.year, bdate.month)
        if month_key not in monthly_months:
            monthly_months[month_key] = bid
        if len(monthly_months) == 12:
            break
    keep_ids.update(monthly_months.values())

    # Backups to delete are those not in keep list
    delete_ids = [bid for bid, _ in valid_backups if bid not in keep_ids]

    return sorted(list(keep_ids)), sorted(delete_ids)
