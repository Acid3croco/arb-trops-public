from datetime import datetime
from dataclasses import dataclass

from db_handler.wrapper import DBWrapper
from arb_defines.arb_dataclasses import Instrument


@dataclass
class InstrInfos:
    bases: list[str] | None = None
    quotes: list[str] | None = None
    exchanges: list[str] | None = None
    instr_types: list[str] | None = None
    contract_types: list[str] | None = None

    def __post_init__(self):
        if self.bases:
            self.bases = [t.upper() for t in self.bases]
        if self.quotes:
            self.quotes = [t.upper() for t in self.quotes]
        if self.exchanges:
            self.exchanges = [t.upper() for t in self.exchanges]
        if self.instr_types:
            self.instr_types = [t.lower() for t in self.instr_types]
        if self.contract_types:
            self.contract_types = [t.lower() for t in self.contract_types]

    def get_from_db(self, **kwargs) -> list[Instrument]:
        db_wrapper = DBWrapper()
        instrs = db_wrapper.get_instruments(
            kwargs.get('bases', self.bases),
            kwargs.get('quotes', self.quotes),
            kwargs.get('instr_types', self.instr_types),
            kwargs.get('exchanges', self.exchanges),
            kwargs.get('contract_types', self.contract_types),
        )
        return [
            i for i in instrs
            if not i.expiry or i.expiry.date() >= datetime.utcnow().date()
        ]


def resolve_instruments_from_ids(instr_ids) -> list[Instrument]:
    db_wrapper = DBWrapper()
    return db_wrapper.get_instruments_with_ids(instr_ids)


def resolve_instruments_from_infos(args, **kwargs) -> list[Instrument]:
    instr_infos = InstrInfos(args.bases, args.quotes, args.exchanges,
                             args.instr_types, args.contract_types)
    return instr_infos.get_from_db(**kwargs)


def _has_args(args):
    if args.instr_ids:
        return True
    # Useless because of default args -> will always be True
    if args.bases or args.quotes or args.exchanges or args.instr_types or args.contract_types:
        return True
    return False


def resolve_instruments(args, **kwargs) -> list[Instrument]:
    if not _has_args(args):
        return None
    if args.instr_ids:
        return resolve_instruments_from_ids(args.instr_ids)
    return resolve_instruments_from_infos(args, **kwargs)
