from __future__ import annotations

from collections import deque
from datetime import date, datetime, time
from decimal import Decimal
from functools import partial
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv4Network,
    IPv6Address,
    IPv6Interface,
    IPv6Network,
)
from pathlib import Path, PurePath
from re import Pattern
from typing import TYPE_CHECKING, Any, Callable, Mapping, TypeVar, overload
from uuid import UUID

import msgspec

from advanced_alchemy.config.types import Empty, EmptyType, TypeDecodersSequence
from advanced_alchemy.exceptions import SerializationError

if TYPE_CHECKING:
    from advanced_alchemy.config.types import TypeEncodersMap

__all__ = (
    "decode_json",
    "default_deserializer",
    "default_serializer",
    "encode_json",
)

T = TypeVar("T")

DEFAULT_TYPE_ENCODERS: TypeEncodersMap = {
    Path: str,
    PurePath: str,
    IPv4Address: str,
    IPv4Interface: str,
    IPv4Network: str,
    IPv6Address: str,
    IPv6Interface: str,
    IPv6Network: str,
    datetime: lambda val: val.isoformat(),
    date: lambda val: val.isoformat(),
    time: lambda val: val.isoformat(),
    deque: list,
    Decimal: lambda val: int(val) if val.as_tuple().exponent >= 0 else float(val),
    Pattern: lambda val: val.pattern,
    # support subclasses of stdlib types, If no previous type matched, these will be
    # the last type in the mro, so we use this to (attempt to) convert a subclass into
    # its base class. # see https://github.com/jcrist/msgspec/issues/248
    # and https://github.com/litestar-org/litestar/issues/1003
    str: str,
    int: int,
    float: float,
    set: set,
    frozenset: frozenset,
    bytes: bytes,
}


def default_serializer(value: Any, type_encoders: Mapping[Any, Callable[[Any], Any]] | None = None) -> Any:
    """Transform values non-natively supported by ``msgspec``

    Args:
        value: A value to serialized
        type_encoders: Mapping of types to callables to transforming types
    Returns:
        A serialized value
    Raises:
        TypeError: if value is not supported
    """
    type_encoders = {**DEFAULT_TYPE_ENCODERS, **(type_encoders or {})}

    for base in value.__class__.__mro__[:-1]:
        try:
            encoder = type_encoders[base]
            return encoder(value)
        except KeyError:
            continue

    msg = f"Unsupported type: {type(value)!r}"
    raise TypeError(msg)


def default_deserializer(
    target_type: Any,
    value: Any,
    type_decoders: TypeDecodersSequence | None = None,
) -> Any:  # pragma: no cover
    """Transform values non-natively supported by ``msgspec``

    Args:
        target_type: Encountered type
        value: Value to coerce
        type_decoders: Optional sequence of type decoders

    Returns:
        A ``msgspec``-supported type
    """

    if isinstance(value, target_type):
        return value

    if type_decoders:
        for predicate, decoder in type_decoders:
            if predicate(target_type):
                return decoder(target_type, value)

    if issubclass(target_type, (Path, PurePath, UUID)):
        return target_type(value)

    msg = f"Unsupported type: {type(value)!r}"
    raise TypeError(msg)


_msgspec_json_encoder = msgspec.json.Encoder(enc_hook=default_serializer)
_msgspec_json_decoder = msgspec.json.Decoder(dec_hook=default_deserializer)


def encode_json(value: Any, serializer: Callable[[Any], Any] | None = None) -> bytes:
    """Encode a value into JSON.

    Args:
        value: Value to encode
        serializer: Optional callable to support non-natively supported types.

    Returns:
        JSON as bytes

    Raises:
        SerializationError: If error encoding ``obj``.
    """
    try:
        return msgspec.json.encode(value, enc_hook=serializer) if serializer else _msgspec_json_encoder.encode(value)
    except (TypeError, msgspec.EncodeError) as msgspec_error:
        raise SerializationError(str(msgspec_error)) from msgspec_error


@overload
def decode_json(value: str | bytes) -> Any:
    ...


@overload
def decode_json(value: str | bytes, type_decoders: TypeDecodersSequence | None) -> Any:
    ...


@overload
def decode_json(value: str | bytes, target_type: type[T]) -> T:
    ...


@overload
def decode_json(value: str | bytes, target_type: type[T], type_decoders: TypeDecodersSequence | None) -> T:
    ...


def decode_json(  # type: ignore  # noqa: PGH003
    value: str | bytes,
    target_type: type[T] | EmptyType = Empty,  # pyright: ignore  # noqa: PGH003
    type_decoders: TypeDecodersSequence | None = None,
) -> Any:
    """Decode a JSON string/bytes into an object.

    Args:
        value: Value to decode
        target_type: An optional type to decode the data into
        type_decoders: Optional sequence of type decoders

    Returns:
        An object

    Raises:
        SerializationError: If error decoding ``value``.
    """
    try:
        if target_type is Empty:
            return _msgspec_json_decoder.decode(value)
        return msgspec.json.decode(
            value,
            dec_hook=partial(default_deserializer, type_decoders=type_decoders),
            type=target_type,
        )
    except msgspec.DecodeError as msgspec_error:
        raise SerializationError(str(msgspec_error)) from msgspec_error
