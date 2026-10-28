# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import typing


class PublicMetric(gl.Contract):
    """
    PublicMetric - a tolerance-based public numeric metric oracle.

    Some public numbers are worth putting on-chain (a repo's star
    count, a project's download total, a registry's entry count)
    but they move between validator runs, so exact equality is
    the wrong consensus rule: it would reject honest readings
    that differ by a handful of units. This contract makes the
    tolerance explicit and part of the request itself.

    The submitter fixes, at request time: the source page, a
    plain-language description of the number to read, and a
    tolerance in basis points (100 = 1%, 1000 = 10%). The
    validator rule is then written in code, not in prose:
    a validator accepts the leader's value only if its own
    freshly read value is within that tolerance band, checked
    with integer cross-multiplication (no floating point):

        |leader - validator| * 10000 <= leader * tolerance_bps

    If validators disagree outside the band, the transaction
    does not finalise and the request stays PENDING - a failed
    consensus is never silently stored as a wrong number.
    The LLM only extracts digits; it never decides whether
    the value is acceptable. That decision is the validator
    function, and it is deterministic code.
    """

    request_count: u256
    names: TreeMap[u256, str]
    source_urls: TreeMap[u256, str]
    fields: TreeMap[u256, str]
    tolerances: TreeMap[u256, u256]
    statuses: TreeMap[u256, str]
    values: TreeMap[u256, u256]

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"

    def __init__(self):
        self.request_count = u256(0)

    @gl.public.write
    def request_metric(
        self, name: str, source_url: str, field: str, tolerance_bps: int
    ) -> int:
        name = name.strip()
        source_url = source_url.strip()
        field = field.strip()

        assert len(name) >= 2 and len(name) <= 100, "bad metric name"
        assert source_url.startswith("https://"), "source must be https"
        assert len(source_url) <= 300, "source URL too long"
        assert len(field) >= 10 and len(field) <= 300, "field description too short"
        assert 100 <= tolerance_bps <= 1000, "tolerance must be 100-1000 bps (1%-10%)"

        rid = self.request_count
        self.names[rid] = name
        self.source_urls[rid] = source_url
        self.fields[rid] = field
        self.tolerances[rid] = u256(tolerance_bps)
        self.statuses[rid] = self.PENDING
        self.values[rid] = u256(0)
        self.request_count = rid + u256(1)
        return int(rid)

    @gl.public.write
    def verify_metric(self, request_id: int) -> int:
        rid = u256(request_id)
        assert rid in self.statuses, "unknown request"
        assert self.statuses[rid] == self.PENDING, "request already verified"

        # Copy storage into locals: non-deterministic blocks may not
        # touch contract storage, they may only capture local values.
        source_url = self.source_urls[rid]
        field = self.fields[rid]
        tolerance_bps = int(self.tolerances[rid])

        def read_metric() -> int:
            page = gl.nondet.web.render(source_url, mode="text")
            prompt = f"""Extract one number from the page below.

Number to extract: {field}
Reply with exactly the number, digits only, no commas, no units,
no explanation, nothing else.

Page content:
{page[:5000]}"""
            raw = gl.nondet.exec_prompt(prompt).strip()
            digits = "".join(ch for ch in raw if ch.isdigit())
            assert len(digits) > 0, "no number found on the page"
            return int(digits)

        def validator_fn(leader_result) -> bool:
            if not isinstance(leader_result, gl.vm.Return):
                return False
            leader_value = leader_result.calldata
            try:
                my_value = read_metric()
            except Exception:
                return False
            if leader_value == 0:
                return my_value == 0
            diff = leader_value - my_value
            if diff < 0:
                diff = -diff
            # |leader - mine| * 10000 <= leader * tolerance_bps
            return diff * 10000 <= leader_value * tolerance_bps

        value = gl.vm.run_nondet_unsafe(read_metric, validator_fn)
        assert value > 0, "extracted value must be positive"
        self.values[rid] = u256(value)
        self.statuses[rid] = self.VERIFIED
        return int(value)

    @gl.public.view
    def get_metric(self, request_id: int) -> typing.Any:
        rid = u256(request_id)
        assert rid in self.statuses, "unknown request"
        return {
            "id": request_id,
            "name": self.names[rid],
            "source_url": self.source_urls[rid],
            "field": self.fields[rid],
            "tolerance_bps": int(self.tolerances[rid]),
            "status": self.statuses[rid],
            "value": int(self.values[rid]),
        }

    @gl.public.view
    def is_verified(self, request_id: int) -> bool:
        rid = u256(request_id)
        assert rid in self.statuses, "unknown request"
        return self.statuses[rid] == self.VERIFIED

    @gl.public.view
    def get_request_count(self) -> int:
        return int(self.request_count)
