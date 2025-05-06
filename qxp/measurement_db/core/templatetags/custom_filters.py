from django import template


register = template.Library()

@register.filter
def format_timedelta(value):
    """ Display a duration as 3h 24m 02s. """
    seconds = round(value.total_seconds())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    res = ""
    if hours:
        res += f"{hours}h "
    if minutes:
        if hours:
            res += f"{minutes:02d}m "
        else:
            res += f"{minutes}m "
    if hours or minutes:
        res += f"{seconds:02d}s"
    else:
        res += f"{seconds}s"
    return res
