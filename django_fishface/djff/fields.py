import pickle
from django.db import models
import numpy as np
import south.modelsinspector as smi
import fishface.hopperchain as hc


class HopperchainSpecField(models.Field):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        super(HopperchainSpecField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'TextField'

    def to_python(self, value):
        if isinstance(value, basestring):
            return hc.string_to_spec(value)

        return value

    def get_prep_value(self, value):
        return hc.spec_to_string(value)

smi.add_introspection_rules([], [r"^djff.fields.HopperchainSpecField"])


class PickleField(models.Field):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        if 'default' in kwargs:
            kwargs['default'] = pickle.dumps(kwargs['default'])
        else:
            kwargs['default'] = 0

        super(PickleField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'TextField'

    def to_python(self, value):
        if isinstance(value, basestring):
            return pickle.loads(str(value))
        return value

    def get_prep_value(self, value):
        return pickle.dumps(value)
smi.add_introspection_rules([], [r"^djff.fields.PickleField"])


class LocationField(PickleField):
    """
    For storing pairs of integers (indexed into a numpy array that
    represents an image.
    """
    pass
smi.add_introspection_rules([], [r"^djff.fields.LocationField"])


class ContourField(PickleField):
    """
    For storing an OpenCV contour.
    """
    # TODO: describe the format of a contour (list of lists of points?)
    pass
smi.add_introspection_rules([], [r"^djff.fields.ContourField"])


class NumpyArrayField(PickleField):
    """
    For storing numpy arrays.
    """
    pass
smi.add_introspection_rules([], [r"^djff.fields.NumpyArrayField"])
