from utils.chia.sized_bytes import bytes32
from utils.chia.hash import std_hash
from utils.chia.bech32m import decode_puzzle_hash
from blspy import AugSchemeMPL, G1Element, PrivateKey
from secrets import token_bytes


def calculate_plot_id_pk(
        pool_public_key: G1Element,
        plot_public_key: G1Element,
) -> bytes32:
    return std_hash(bytes(pool_public_key) + bytes(plot_public_key))


def get_plot_id(
        pool_public_key: G1Element,
        plot_public_key: G1Element,
) -> bytes32:
    return calculate_plot_id_pk(pool_public_key, plot_public_key)


def _derive_path(sk: PrivateKey, path: list) -> PrivateKey:
    for index in path:
        sk = AugSchemeMPL.derive_child_sk(sk, index)
    return sk


def master_sk_to_local_sk(master: PrivateKey) -> PrivateKey:
    return _derive_path(master, [12381, 8444, 3, 0])


def generate_taproot_sk(local_pk: G1Element, farmer_pk: G1Element) -> PrivateKey:
    taproot_message: bytes = bytes(local_pk + farmer_pk) + bytes(local_pk) + bytes(farmer_pk)
    taproot_hash: bytes32 = std_hash(taproot_message)
    return AugSchemeMPL.key_gen(taproot_hash)


def generate_plot_public_key(local_pk: G1Element, farmer_pk: G1Element, include_taproot: bool = False) -> G1Element:
    if include_taproot:
        taproot_sk: PrivateKey = generate_taproot_sk(local_pk, farmer_pk)
        return local_pk + farmer_pk + taproot_sk.get_g1()
    else:
        return local_pk + farmer_pk

    # return local_pk + farmer_pk


def stream_plot_info_pk(
    pool_public_key: G1Element,
    farmer_public_key: G1Element,
    local_master_sk: PrivateKey,
):
    # There are two ways to stream plot info: with a pool public key, or with a pool contract puzzle hash.
    # This one streams the public key, into bytes
    data = bytes(pool_public_key) + bytes(farmer_public_key) + bytes(local_master_sk)
    assert len(data) == (48 + 48 + 32)
    return data


def calculate_plot_id_ph(
    pool_contract_puzzle_hash: bytes32,
    plot_public_key: G1Element,
) -> bytes32:
    return std_hash(bytes(pool_contract_puzzle_hash) + bytes(plot_public_key))


def stream_plot_info_ph(
    pool_contract_puzzle_hash: bytes32,
    farmer_public_key: G1Element,
    local_master_sk: PrivateKey,
):
    # There are two ways to stream plot info: with a pool public key, or with a pool contract puzzle hash.
    # This one streams the pool contract puzzle hash, into bytes
    data = pool_contract_puzzle_hash + bytes(farmer_public_key) + bytes(local_master_sk)
    return data


def get_plot_id_and_memo(farmer_public_key: str, pool_public_key: str, pool_contract_address: str):
    if farmer_public_key.startswith('0x'):
        farmer_public_key = farmer_public_key[2:]
    if pool_public_key.startswith('0x'):
        pool_public_key = pool_public_key[2:]

    pool_contract_puzzle_hash = None
    if pool_public_key:
        pool_public_key = G1Element.from_bytes(bytes.fromhex(pool_public_key))
    elif pool_contract_address:
        pool_contract_puzzle_hash = decode_puzzle_hash(pool_contract_address)

    farmer_public_key = G1Element.from_bytes(bytes.fromhex(farmer_public_key))
    sk = AugSchemeMPL.key_gen(token_bytes(32))

    plot_public_key = generate_plot_public_key(master_sk_to_local_sk(sk).get_g1(), farmer_public_key, pool_contract_puzzle_hash is not None)

    if pool_public_key:
        plot_id: bytes32 = calculate_plot_id_pk(pool_public_key, plot_public_key)
        plot_memo: bytes32 = stream_plot_info_pk(pool_public_key, farmer_public_key, sk)
    elif pool_contract_puzzle_hash:
        plot_id = calculate_plot_id_ph(pool_contract_puzzle_hash, plot_public_key)
        plot_memo = stream_plot_info_ph(pool_contract_puzzle_hash, farmer_public_key, sk)

    return plot_id.hex(), plot_memo.hex()
