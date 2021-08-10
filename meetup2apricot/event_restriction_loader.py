"""Loads event restrictions from a configuration list.

A configuration list contains JSON objects converted to Python dicts with these keys:

    name: the event registration type name such as RSVP. (Default: RSVP)

    pattern: a regex pattern to find within the event name. (Default: match all
    event names)

    price: "free" or "paid" to match only free or paid events. (Default: match
    both free and paid events)

    levels: a member level name such as Associate or a list of such names.
    (Default: all member levels are selected)
"""

from .exceptions import InvalidPriceRestriction, InvalidRestrictionPattern
from collections import namedtuple
import re


class EventRestriction(
    namedtuple(
        "EventRestriction",
        "name pattern match_free_events match_paid_events member_levels",
    )
):

    """Event restrictions can match an event based on the event title or price.
    Event restrictions provide an event registration type name and a list of
    names of member levels allowed to register."""

    __slots__ = ()

    def matches_price(self, price):
        """Return true if the price matches the free/paid event flags."""
        return self.match_free_events if price == 0 else self.match_paid_events


class EventRestrictionLoader:

    """Loads event restrictions from a list, compiling title patterns, and
    validating member levels."""

    def __init__(self, member_level_manager):
        """Initialize with a member level manager."""
        self.member_level_manager = member_level_manager

    def load(self, restriction_list):
        """Load restrictions from a list of restriction JSON objects, typically
        from the environment configuration.  Return a list of EventRestriction
        objects."""
        event_restrictions = [
            self.load_restriction(restriction) for restriction in restriction_list
        ]
        default_restriction = self.load_restriction({})
        event_restrictions.append(default_restriction)
        return event_restrictions

    def load_restriction(self, restriction):
        """Load a restriction JSON object, typically from the environment
        configuration.  Return an EventRestriction object."""
        name = restriction.get("name", "RSVP")
        pattern = self.compile_pattern(restriction.get("pattern", "^"))
        match_free_events, match_paid_events = self.parse_price(
            restriction.get("price", "")
        )
        level_names = self.clean_level_names(restriction.get("levels", []))
        member_levels = self.lookup_member_levels(level_names)
        return EventRestriction(
            name, pattern, match_free_events, match_paid_events, member_levels
        )

    def lookup_member_levels(self, level_names):
        """Given a list of member level names, return a corresponding list of
        member levels. If the level name list is empty, return all member
        levels."""
        if level_names:
            return self.member_level_manager.named_levels(level_names)
        else:
            return self.member_level_manager.all_levels()

    @staticmethod
    def compile_pattern(pattern):
        """Compile a title patten. Return the compiled pattern."""
        try:
            return re.compile(pattern, re.IGNORECASE)
        except re.error as err:
            message = f"Event restriction pattern {pattern!r} is invalid: {err}"
            raise InvalidRestrictionPattern(message) from err

    @staticmethod
    def parse_price(price_restriction):
        """Parse the price restriction (free, paid, or blank) and return flags
        to match free and paid events."""
        match_free_events = True
        match_paid_events = True
        if price_restriction == "free":
            match_paid_events = False
        elif price_restriction == "paid":
            match_free_events = False
        elif price_restriction != "":
            message = (
                f'Event price restriction "{price_restriction}" '
                'must be "free", "paid", or omitted'
            )
            raise InvalidPriceRestriction(message)
        return match_free_events, match_paid_events

    @staticmethod
    def clean_level_names(raw_level_names):
        """Give a list of member level names, an individual member level name,
        or None, return a possibly empty list of member level names."""
        if not raw_level_names:
            return []
        if type(raw_level_names) == str:
            return [raw_level_names]
        return raw_level_names


# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4 autoindent
