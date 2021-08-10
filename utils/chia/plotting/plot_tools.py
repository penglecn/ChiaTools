from typing import Tuple, Union
from utils.chia.sized_bytes import bytes32
from blspy import G1Element, PrivateKey


def parse_plot_info(memo: bytes) -> Tuple[bool, str, str, str]:
    # Parses the plot info bytes into keys
    if len(memo) == (48 + 48 + 32):
        # This is a public key memo
        return (
            False,
            f'{G1Element.from_bytes(memo[:48])}',
            f'{G1Element.from_bytes(memo[48:96])}',
            f'{PrivateKey.from_bytes(memo[96:])}',
        )
    elif len(memo) == (32 + 48 + 32):
        # This is a pool_contract_puzzle_hash memo
        return (
            True,
            f'{bytes32(memo[:32])}',
            f'{G1Element.from_bytes(memo[32:80])}',
            f'{PrivateKey.from_bytes(memo[80:])}',
        )
    else:
        raise ValueError(f"Invalid number of bytes {len(memo)}")
