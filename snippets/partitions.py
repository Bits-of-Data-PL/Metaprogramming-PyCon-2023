IGNORE_TABLES_REGEX = r'.+_[0-9]{6}$'


def get_partition_statement(suffix):
    """
    >>> get_partition_statement('202005')
    "FOR VALUES FROM ('2020-05-01') TO ('2020-06-01')"
    >>> get_partition_statement('202112')
    "FOR VALUES FROM ('2021-12-01') TO ('2022-01-01')"
    >>> get_partition_statement('202101')
    "FOR VALUES FROM ('2021-01-01') TO ('2021-02-01')"
    >>> get_partition_statement('202111')
    "FOR VALUES FROM ('2021-11-01') TO ('2021-12-01')"
    """
    year = int(suffix[:4])
    month = int(suffix[-2:])
    nextyear = year + (1 if month == 12 else 0)
    nextmonth = (month + 1 if month < 12 else 1)
    return f"FOR VALUES FROM ('{year}-{month:02d}-01') TO ('{nextyear}-{nextmonth:02d}-01')"


class PartitionByMeta(DeclarativeMeta):
    def __new__(cls, clsname, bases, attrs, *, partition_by, partition_type):

        @classmethod
        def get_partition_name(cls_, suffix):
            return f'{cls_.__tablename__}_{suffix}'

        @classmethod
        def create_partition(cls_, suffix, subpartition_by=None, subpartition_type=None):
            if suffix not in cls_.partitions:
                partition = PartitionByMeta(
                    f'{clsname}{suffix}',
                    bases,
                    {'__tablename__': cls_.get_partition_name(suffix)},
                    partition_type=subpartition_type,
                    partition_by=subpartition_by,
                )

                partition.__table__.add_is_dependent_on(cls_.__table__)
                partition_stmt = get_partition_statement(suffix)
                event.listen(
                    partition.__table__,
                    'after_create',
                    DDL(
                        # For non-year ranges, modify the FROM and TO below
                        # LIST: IN ('first', 'second');
                        # RANGE: FROM ('{key}-01-01') TO ('{key+1}-01-01')
                        f"""
                        ALTER TABLE {cls_.__tablename__}
                        ATTACH PARTITION {partition.__tablename__}
                        {partition_stmt};
                        """
                    )
                )

                cls_.partitions[suffix] = partition

            return cls_.partitions[suffix]

        if partition_by is not None:
            attrs.update(
                {
                    '__table_args__': attrs.get('__table_args__', ())
                                      + (dict(postgresql_partition_by=f'{partition_type.upper()}({partition_by})'),),
                    'partitions': {},
                    'partitioned_by': partition_by,
                    'get_partition_name': get_partition_name,
                    'create_partition': create_partition
                }
            )

        return super().__new__(cls, clsname, bases, attrs)


class EnumWrapper(db.TypeDecorator):
    impl = db.String(TYPE_LEN)

    @property
    def python_type(self):
        return self.__class__.impl

    def process_literal_param(self, value, dialect):
        return value

    def process_bind_param(self, value, dialect):
        return value.name

    def process_result_value(self, value, dialect):
        return self.__class__.cls(value)


class EventType(EnumMixin, Base):
    class Values(ShortReprMixin, AutoEnumBase):
        EVENT_TYPE_NEW = auto()
        EVENT_TYPE_ACTIVITY = auto()
        EVENT_TYPE_PURCHASE = auto()
        EVENT_TYPE_NOTPURCHASE = auto()
        EVENT_TYPE_TRANSACTION = auto()
        EVENT_TYPE_ELAPSED_TIME = auto()
        EVENT_TYPE_CLASSIC_STAMPS = auto()
        EVENT_TYPE_ONE_OFF = auto()
        EVENT_TYPE_INVITE = auto()
        EVENT_TYPE_CONFIRMATION = auto()
        EVENT_TYPE_REJECTION = auto()
        EVENT_TYPE_CANCELLATION = auto()


class EventTypeWrapper(EnumWrapper):
    cls = EventType.Values


class PartitionMixin:
    id = db.Column(UUID(as_uuid=True), primary_key=True, index=True, nullable=False, default=generate_uuid)
    created = db.Column(db.DateTime, primary_key=True, nullable=False, server_default=func.now())
    modified = db.Column(db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class EventPartitionMixin(PartitionMixin):
    slug = db.Column(db.String(32), nullable=False)
    consumer_id = db.Column(UUID(as_uuid=True), nullable=False)
    type = db.Column(EventTypeWrapper, nullable=False)
    payload = db.Column(JSON(), nullable=False, default={})


class MessagePartitionMixin(PartitionMixin):
    slug = db.Column(db.String(32), nullable=False, unique=False, index=True)
    email = db.Column(db.String(128), nullable=False, unique=False, index=True)
    consumer_id = db.Column(UUID(as_uuid=True), nullable=False, index=True)
    subject = db.Column(db.String(128), nullable=False, default='')
    body = db.Column(db.String(512), nullable=False, default='')


class Message(MessagePartitionMixin, Base, metaclass=PartitionByMeta, partition_by='created', partition_type='RANGE'):
    __table_args__ = (
        db.Index('message_email_slug_idx', 'email', 'slug'),
    )


class Event(EventPartitionMixin, Base, metaclass=PartitionByMeta, partition_by='created', partition_type='RANGE'):
    pass
