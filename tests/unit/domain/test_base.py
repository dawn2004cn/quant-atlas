"""Tests for domain/base.py — Entity, ValueObject, AggregateRoot, DomainEvent."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from app.domain.base import (
    AggregateRoot,
    DateRange,
    Entity,
    EntityFactory,
    IDomainService,
    IRepository,
    IQueryRepository,
    Money,
    Percentage,
    DomainEvent,
)


# ======================================================================
# Entity tests
# ======================================================================


class TestEntity:
    """Tests for the base Entity class."""

    def test_entity_has_default_uuid(self):
        entity = Entity()
        assert entity.id is not None
        assert isinstance(entity.id, uuid4().__class__)

    def test_entity_has_default_timestamps(self):
        entity = Entity()
        assert entity.created_at is not None
        assert entity.updated_at is not None

    def test_touch_updates_timestamp(self):
        entity = Entity()
        old = entity.updated_at
        entity.touch()
        assert entity.updated_at >= old

    def test_equality_by_id(self):
        id1 = uuid4()
        id2 = uuid4()
        e1 = Entity(id=id1)
        e2 = Entity(id=id1)
        e3 = Entity(id=id2)
        assert e1 == e2
        assert e1 != e3
        assert not (e1 == "not an entity")

    def test_hash_consistency(self):
        id1 = uuid4()
        e1 = Entity(id=id1)
        e2 = Entity(id=id1)
        assert hash(e1) == hash(e2)


# ======================================================================
# ValueObject tests
# ======================================================================


class TestDateRange:
    """Tests for the DateRange value object."""

    def test_contains(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        dr = DateRange(start=start, end=end)
        assert dr.contains(datetime(2024, 6, 15))
        assert not dr.contains(datetime(2025, 1, 1))
        assert not dr.contains(datetime(2023, 12, 31))

    def test_days(self):
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 10)
        dr = DateRange(start=start, end=end)
        assert dr.days == 9

    def test_frozen(self):
        dr = DateRange(start=datetime(2024, 1, 1), end=datetime(2024, 12, 31))
        try:
            dr.start = datetime(2025, 1, 1)  # type: ignore[assignment]
            assert False, "Expected FrozenInstanceError"
        except (TypeError, Exception):
            pass


class TestPercentage:
    """Tests for the Percentage value object."""

    def test_from_decimal(self):
        p = Percentage.from_decimal(0.75)
        assert p.value == 0.75

    def test_from_percent(self):
        p = Percentage.from_percent(75)
        assert p.value == 0.75

    def test_decimal_property(self):
        p = Percentage.from_percent(50)
        assert p.decimal == 0.5

    def test_percent_property(self):
        p = Percentage.from_decimal(0.25)
        assert p.percent == 25.0

    def test_str(self):
        p = Percentage.from_percent(33)
        assert str(p) == "33.00%"

    def test_frozen(self):
        p = Percentage(value=0.5)
        try:
            p.value = 0.6  # type: ignore[assignment]
            assert False, "Expected FrozenInstanceError"
        except (TypeError, Exception):
            pass


class TestMoney:
    """Tests for the Money value object."""

    def test_defaults_cny(self):
        m = Money(amount=1000.0)
        assert m.currency == "CNY"
        assert str(m) == "CNY 1,000.00"

    def test_usd(self):
        m = Money(amount=99.99, currency="USD")
        assert m.currency == "USD"
        assert str(m) == "USD 99.99"


# ======================================================================
# AggregateRoot tests
# ======================================================================


class TestAggregateRoot:
    """Tests for the AggregateRoot class."""

    def test_has_empty_events_initially(self):
        ar = AggregateRoot()
        assert ar.pull_events() == []

    def test_add_and_pull_events(self):
        ar = AggregateRoot()
        event = DomainEvent()
        ar.add_event(event)
        pulled = ar.pull_events()
        assert len(pulled) == 1
        assert pulled[0] is event
        # Second pull is empty
        assert ar.pull_events() == []


# ======================================================================
# Repository interface tests
# ======================================================================


class TestIDomainService:
    """Tests for the IDomainService interface marker."""

    def test_is_abstract(self):
        class ConcreteService(IDomainService):
            pass

        svc = ConcreteService()
        assert isinstance(svc, IDomainService)


# ======================================================================
# EntityFactory tests
# ======================================================================


class TestEntityFactory:
    """Tests for EntityFactory."""

    def test_create_entity(self):
        """EntityFactory.create passes kwargs to the constructor."""
        result = EntityFactory.create(Entity)
        assert result.id is not None

    def test_create_entity_with_id(self):
        custom_id = uuid4()
        result = EntityFactory.create(Entity, id=custom_id)
        assert result.id == custom_id
