"""miniattrs - a minimal runtime validation dataclass

>>> from miniattrs import define
>>>
>>> @define
... class Pet:
...   name: str
...   age: int
...
>>> tina = Pet(name='tina', age=2)
"""

import copy
import inspect
import sys

if sys.version_info < (3, 11):
    # dummy dataclass transform - not supported
    def dataclass_transform(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

else:
    from typing import dataclass_transform


class _MissingType:
    def __repr__(self):
        return "<MISSING>"


_MISSING = _MissingType()


def field(*args, **kwargs):
    """A function wrapper around `Field`

    This is necessary because `dataclass_transform` is designed
    to match semantics of built-in dataclasses, so we need a
    function specified as a parameter to `field_specifiers`.

    The spec as of date is misleading, because according to it
    `Field` as a field specifier should be sufficient.

    See: https://discuss.python.org/t/using-classes-as-dataclass-transform-field-specifiers/46459
    """
    return Field(*args, **kwargs)


@dataclass_transform(field_specifiers=(field,), kw_only_default=True)
def define(cls):
    """A class decorator that turns a class' type annototations into type validators

    Each annotated attribute becomes a `Field` descriptor that validates that values are of the
    associated type at runtime.
    """

    annotations, annotations_klass = {}, {}

    for klass in reversed(cls.__mro__):
        # walk down the inheritance chain collecting annotations
        klass_annotations = inspect.get_annotations(klass)
        annotations.update(klass_annotations)

        for name in klass_annotations:
            # For each attr, specify the most specific class
            annotations_klass[name] = klass

    if not annotations:
        raise TypeError("@define requires at least one annotated attribute")

    compulsory, optional = [], []
    for name, field_type in annotations.items():
        descriptor_kwargs = {}
        descriptor_instance = None
        attr_with_default = False

        most_specific_class = annotations_klass[name]
        attr = most_specific_class.__dict__.get(name, _MISSING)
        if attr is not _MISSING:
            # attribute exists in the class body
            # determine whether it is a descriptor instance or actual value
            if isinstance(attr, Field):
                descriptor_instance = attr
                attr_with_default = descriptor_instance._has_default()
            else:
                descriptor_kwargs["default"] = attr
                attr_with_default = True

            # determine whether attr is optional or not
            if attr_with_default:
                optional.append(name)
            else:
                compulsory.append(name)
        else:
            # value missing from class body
            compulsory.append(name)

        if descriptor_instance is None:
            descriptor_instance = field(**descriptor_kwargs)

        setattr(cls, name, descriptor_instance)
        descriptor_instance.__set_name__(cls, name)

        descriptor_instance._set_type_validator(field_type, name)

        if descriptor_instance._has_default():
            descriptor_instance._validate_default()

    field_names = compulsory + optional
    init_code = _build_init(compulsory, optional)
    cls.__init__ = _make_init(init_code)
    cls.__eq__ = _make_eq(field_names)
    cls.__repr__ = _make_repr(field_names)
    return cls


class Field:
    """A validating descriptor"""

    _NULL = _MissingType()

    def __init__(self, *, default=_NULL, validators=()):
        self._default = default
        self._validators = tuple(validators)

    def __set_name__(self, owner, name):
        self._field_name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = instance.__dict__.get(self._field_name, self._default)
        if value is self._NULL:
            msg = f"Attribute '{self._field_name}' not set"
            raise AttributeError(msg)

        if value is self._default:
            # Create instance copy on first access
            value = instance.__dict__[self._field_name] = copy.deepcopy(value)
        return value

    def __set__(self, instance, value):
        self.validate(value)
        instance.__dict__[self._field_name] = value

    def validate(self, value):
        for validator in self._validators:
            validator(value)

    def _has_default(self):
        return self._default is not self._NULL

    def _set_type_validator(self, expected_type, attr_name):
        self._validators = (
            _validate_type(expected_type, attr_name),
        ) + self._validators

    def _validate_default(self):
        self.validate(self._default)


def _make_repr(field_names):
    """Creates a __repr__ based on the provided class attributes"""

    def __repr__(self):
        cls_name = type(self).__name__
        kwargs = ", ".join([f"{f}={getattr(self, f)!r}" for f in field_names])
        return f"{cls_name}({kwargs})"

    return __repr__


def _make_eq(field_names):
    """Creates an __eq__ based on comparison of the provided attributes"""

    def __eq__(self, other):
        if type(self) is type(other):
            return all(getattr(self, f) == getattr(other, f) for f in field_names)
        return NotImplemented

    return __eq__


def _make_init(code):
    """Creates an __init__ using the provided Python code"""
    namespace = {"_MISSING": _MISSING}
    exec(code, namespace)
    return namespace["__init__"]


def _build_init(compulsory=None, optional=None):
    """Generates __init__ code using the provided keyword arguments"""

    if not (compulsory or optional):
        raise ValueError(f"Expected compulsory or optional init parameters")

    compulsory_kwargs = ", ".join(compulsory) if compulsory else ""
    optional_kwargs = (
        ", ".join(f"{field}=_MISSING" for field in optional) if optional else ""
    )
    both_provided = all([compulsory, optional])
    kwargs = (
        ", ".join([compulsory_kwargs, optional_kwargs])
        if both_provided
        else compulsory_kwargs + optional_kwargs
    )
    head = f"\ndef __init__(self, *, {kwargs}):\n"
    compulsory_body = (
        [f"    setattr(self, '{n}', {n})\n" for n in compulsory] if compulsory else []
    )
    optional_body = (
        [f"    if {n} is not _MISSING: setattr(self, '{n}', {n})\n" for n in optional]
        if optional
        else []
    )
    return "".join([head] + compulsory_body + optional_body)


def _validate_type(expected_type, attr_name):
    """Creates a type validator for the attribute"""

    def validator(value):
        if not isinstance(value, expected_type):
            expected_type_name = expected_type.__name__
            value_type = type(value).__name__
            raise TypeError(
                f"{attr_name}: expected type {expected_type_name}, instead got type {value_type}"
            )
        return value

    return validator


def validate_length(*, min_length=None, max_length=None):
    """Creates a length validator for a field input"""

    if min_length is not None and not isinstance(min_length, int):
        raise TypeError(f"Expected min_length to be type int, not {type(min_length)}")

    if max_length is not None and not isinstance(max_length, int):
        raise TypeError(f"Expected max_length to be type int, not {type(max_length)}")

    if min_length is not None and max_length is not None and min_length > max_length:
        raise ValueError("min_length cannot be greater than max_length")
    if min_length is not None and min_length < 0:
        raise ValueError("min_length cannot be < 0")
    if max_length is not None and max_length < 0:
        raise ValueError("max_length cannot be < 0")

    def validator(value):
        if min_length is not None and len(value) < min_length:
            raise ValueError(
                f"Expected minimum length of {min_length}, got {len(value)}"
            )
        if max_length is not None and len(value) > max_length:
            raise ValueError(
                f"Expected maximum length of {max_length}, got {len(value)}"
            )

    return validator


def validate_range(*, min_value=None, max_value=None):
    """Creates a range validator for a field input"""

    if min_value is not None:
        _validate_is_comparable(min_value)

    if max_value is not None:
        _validate_is_comparable(max_value)

    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValueError("min_value cannot be greater than max_value")

    def validator(value):
        if min_value is not None and value < min_value:
            raise ValueError(f"Expected minimum value of {min_value}, got {value}")
        if max_value is not None and value > max_value:
            raise ValueError(f"Expected maximum value of {max_value}, got {value}")

    return validator


def _validate_is_comparable(value):
    """Check whether the provided value supports comparisons"""
    try:
        value < value
    except TypeError:
        raise ValueError(f"{value} doesn't support ordering comparisons")
