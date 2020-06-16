#! /usr/bin/env python3
# Tests for gossip_timestamp_filter
from lnprototest import Connect, Block, ExpectMsg, Msg, RawMsg, Funding, LOCAL, REMOTE, MustNotMsg, Disconnect, AnyOrder, Runner, bitfield
from fixtures import *  # noqa: F401,F403
from blocks import BLOCK_102
import unittest
import time


def test_gossip_timestamp_filter(runner: Runner) -> None:
    if runner.has_option('option_gossip_queries') is None:
        unittest.SkipTest('Needs option_gossip_queries')

    funding1_tx = '020000000001016b85f654d8186f4d5dd32a977b2cf8c4b01ff4634152acba16b654c1c85a83160100000000ffffffff01c5410f0000000000220020c46bf3d1686d6dbb2d9244f8f67b90370c5aa2747045f1aeccb77d8187117382024730440220798d96d5a057b5b7797988a855217f41af05ece3ba8278366e2f69763c72e785022065d5dd7eeddc0766ddf65557c92b9c52c301f23f94d2cf681860d32153e6ae1e012102d6a3c2d0cf7904ab6af54d7c959435a452b24a63194e1c4e7c337d3ebbb3017b00000000'

    funding1 = Funding(funding_txid='1d3160756ceeaf5474f389673aafe0484e58260927871ce92f388f72b0409c18',
                       funding_output_index=0,
                       funding_amount=999877,
                       local_node_privkey='02',
                       local_funding_privkey='10',
                       remote_node_privkey='03',
                       remote_funding_privkey='20')

    # Funding tx spending 16835ac8c154b616baac524163f41fb0c4f82c7b972ad35d4d6f18d854f6856b/0, feerate 253 to bitcoin privkeys 0000000000000000000000000000000000000000000000000000000000000030 and 0000000000000000000000000000000000000000000000000000000000000040 (txid db029ee8cc511625887c192c5bb264249fe69b9b86eb627a52f9a313ba231ade)
    funding2_tx = '020000000001016b85f654d8186f4d5dd32a977b2cf8c4b01ff4634152acba16b654c1c85a83160000000000ffffffff0105841e0000000000220020fa73be60259cea454ee79a963514f0b7622db62eadc88daafe377bfa2aa30fbb0247304402205735b9750a90be1ca09cdf91d6697bde3746a390698ca754d516b56c72880bae02203c1deef3645cc20e300db1a808ffc7c2f57be200761ee3cf1a479d1e1aef70bc0121038f1573b4238a986470d250ce87c7a91257b6ba3baf2a0b14380c4e1e532c209d00000000'
    funding2 = Funding(funding_txid='de1a23ba13a3f9527a62eb869b9be69f2464b25b2c197c88251651cce89e02db',
                       funding_output_index=0,
                       funding_amount=1999877,
                       local_node_privkey='04',
                       local_funding_privkey='30',
                       remote_node_privkey='05',
                       remote_funding_privkey='40')

    timestamp1 = int(time.time())
    timestamp2 = timestamp1 + 1

    test = [BLOCK_102,

            Connect(connprivkey='03'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=''),

            # txid 189c40b0728f382fe91c87270926584e48e0af3a6789f37454afee6c7560311d
            Block(blockheight=103, number=6, txs=[funding1_tx]),

            RawMsg(funding1.channel_announcement('103x1x0', '')),
            RawMsg(funding1.node_announcement(LOCAL, '', (1, 2, 3), 'foobar', b'', timestamp1)),

            # New peer connects, asks for gossip_timestamp_filter=all.  We *won't* relay channel_announcement, as there is no channel_update.
            Connect(connprivkey='05'),
            ExpectMsg('init'),
            # BOLT #9:
            # | 6/7   | `gossip_queries`                 | More sophisticated gossip control
            Msg('init', globalfeatures='', features=bitfield(6)),
            Msg('gossip_timestamp_filter', chain_hash='06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f',
                first_timestamp=0, timestamp_range=4294967295),
            MustNotMsg('channel_announcement'),
            MustNotMsg('channel_update'),
            MustNotMsg('node_announcement'),
            Disconnect(),

            # Now, with channel update
            RawMsg(funding1.channel_update(side=LOCAL,
                                           short_channel_id='103x1x0',
                                           disable=False,
                                           cltv_expiry_delta=144,
                                           htlc_minimum_msat=0,
                                           fee_base_msat=1000,
                                           fee_proportional_millionths=10,
                                           timestamp=timestamp1,
                                           htlc_maximum_msat=None),
                   connprivkey='03'),

            # New peer connects, asks for gossip_timestamp_filter=all.  update and node announcement will be relayed.
            Connect(connprivkey='05'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=bitfield(6)),
            Msg('gossip_timestamp_filter', chain_hash='06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f',
                first_timestamp=0, timestamp_range=4294967295),

            ExpectMsg('channel_announcement', short_channel_id='103x1x0'),
            AnyOrder(ExpectMsg('channel_update', short_channel_id='103x1x0'),
                     ExpectMsg('node_announcement')),
            Disconnect(),

            # BOLT #7:
            # The receiver:
            #  - SHOULD send all gossip messages whose `timestamp` is greater or
            #    equal to `first_timestamp`, and less than `first_timestamp` plus
            #    `timestamp_range`.
            Connect(connprivkey='05'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=bitfield(6)),
            Msg('gossip_timestamp_filter', chain_hash='06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f',
                first_timestamp=1000, timestamp_range=timestamp1 - 1000),

            MustNotMsg('channel_announcement'),
            MustNotMsg('channel_update'),
            MustNotMsg('node_announcement'),
            Disconnect(),

            Connect(connprivkey='05'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=bitfield(6)),
            Msg('gossip_timestamp_filter', chain_hash='06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f',
                first_timestamp=timestamp1 + 1, timestamp_range=4294967295),

            MustNotMsg('channel_announcement'),
            MustNotMsg('channel_update'),
            MustNotMsg('node_announcement'),
            Disconnect(),

            # These two succeed in getting the gossip, then stay connected for next test.
            Connect(connprivkey='05'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=bitfield(6)),
            Msg('gossip_timestamp_filter', chain_hash='06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f',
                first_timestamp=timestamp1, timestamp_range=4294967295),

            ExpectMsg('channel_announcement', short_channel_id='103x1x0'),
            AnyOrder(ExpectMsg('channel_update', short_channel_id='103x1x0'),
                     ExpectMsg('node_announcement')),

            Connect(connprivkey='06'),
            ExpectMsg('init'),
            Msg('init', globalfeatures='', features=bitfield(6)),
            Msg('gossip_timestamp_filter', chain_hash='06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f',
                first_timestamp=1000, timestamp_range=timestamp1 - 1000 + 1),

            ExpectMsg('channel_announcement', short_channel_id='103x1x0'),
            AnyOrder(ExpectMsg('channel_update', short_channel_id='103x1x0'),
                     ExpectMsg('node_announcement')),


            # BOLT #7:
            #  - SHOULD restrict future gossip messages to those whose `timestamp`
            #    is greater or equal to `first_timestamp`, and less than
            #    `first_timestamp` plus `timestamp_range`.
            Block(blockheight=109, number=6, txs=[funding2_tx]),

            RawMsg(funding2.channel_announcement('109x1x0', ''),
                   connprivkey='03'),
            RawMsg(funding2.channel_update(side=LOCAL,
                                           short_channel_id='109x1x0',
                                           disable=False,
                                           cltv_expiry_delta=144,
                                           htlc_minimum_msat=0,
                                           fee_base_msat=1000,
                                           fee_proportional_millionths=10,
                                           timestamp=timestamp2,
                                           htlc_maximum_msat=None)),
            RawMsg(funding2.channel_update(side=REMOTE,
                                           short_channel_id='109x1x0',
                                           disable=False,
                                           cltv_expiry_delta=144,
                                           htlc_minimum_msat=0,
                                           fee_base_msat=1000,
                                           fee_proportional_millionths=10,
                                           timestamp=timestamp2,
                                           htlc_maximum_msat=None)),
            RawMsg(funding2.node_announcement(LOCAL, '', (1, 2, 3), 'foobar2', b'', timestamp2)),

            # 005's filter covers this, 006's doesn't.
            ExpectMsg('channel_announcement', short_channel_id='109x1x0', connprivkey='05'),
            AnyOrder(ExpectMsg('channel_update', short_channel_id='109x1x0', channel_flags=0),
                     ExpectMsg('channel_update', short_channel_id='109x1x0', channel_flags=1),
                     ExpectMsg('node_announcement')),

            MustNotMsg('channel_announcement', connprivkey='06'),
            MustNotMsg('channel_update'),
            MustNotMsg('node_announcement')]

    runner.run(test)
