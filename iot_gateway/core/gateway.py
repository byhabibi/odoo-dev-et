last_value = {}

def process(machine_code, current_value):
    prev = last_value.get(machine_code, current_value)

    delta = current_value - prev

    if delta < 0:
        delta = current_value  # reset

    last_value[machine_code] = current_value

    return delta