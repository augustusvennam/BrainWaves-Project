"""Interpret samples using Cortex's subscription schema, never guessed indices."""
import math

EEG_CHANNELS = frozenset('AF3 F7 F3 FC5 T7 P7 O1 O2 P8 T8 FC6 F4 F8 AF4 AFz Fz Cz Pz POz'.split())


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def map_columns(columns, values):
    if not isinstance(columns, list) or not isinstance(values, list) or len(columns) != len(values):
        raise ValueError('Sample does not match its subscription columns.')
    result = {}
    for column, value in zip(columns, values):
        if isinstance(column, list):
            nested = map_columns(column, value)
            if result.keys() & nested.keys():
                raise ValueError('Duplicate subscription columns.')
            result.update(nested)
        elif isinstance(column, str):
            if column in result:
                raise ValueError('Duplicate subscription columns.')
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError('Non-finite sample value.')
            result[column] = value
        else:
            raise ValueError('Unsupported subscription column.')
    return result


def normalize_sample(stream, columns, payload):
    timestamp = payload.get('time')
    if not finite_number(timestamp):
        raise ValueError('Sample timestamp must be a finite Unix time in seconds.')
    values = map_columns(columns, payload.get(stream))
    if stream == 'eeg':
        channels = {key: value for key, value in values.items() if key in EEG_CHANNELS}
        if not channels or not all(finite_number(value) for value in channels.values()):
            raise ValueError('EEG sample has missing or nonnumeric sensor amplitudes.')
        return {'time': timestamp, 'values': channels, 'interpolated': values.get('INTERPOLATED') == 1}
    if stream == 'met':
        metrics = {}
        for key, value in values.items():
            if key.endswith('.isActive'):
                continue
            active = values.get(f'{key}.isActive', True)
            metrics[key] = value if active is True and finite_number(value) and 0 <= value <= 1 else None
        return {'time': timestamp, 'values': metrics}
    if stream == 'pow':
        bands = {key: value for key, value in values.items() if '/' in key}
        if not bands or not all(finite_number(value) and value >= 0 for value in bands.values()):
            raise ValueError('Invalid band power sample.')
        return {'time': timestamp, 'values': bands}
    if stream == 'com':
        if not isinstance(values.get('act'), str) or not finite_number(values.get('pow')) or not 0 <= values['pow'] <= 1:
            raise ValueError('Invalid mental command sample.')
    if stream in {'eq', 'dev'}:
        if not all(finite_number(value) for value in values.values()):
            raise ValueError('Invalid device quality sample.')
    return {'time': timestamp, 'values': values}
