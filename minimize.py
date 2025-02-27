#!/usr/bin/python
from datetime import datetime
import sqlite3
import msgpack
import zlib
import csv


class TraceMinimizer:
    def __init__(self, db_path, out_file):
        self.sql = sqlite3.connect(db_path)
        self.c = self.sql.cursor()
        self.out = out_file

        self.master_bblock = {}
        self.master_bbcount = {}
        self.master_inscount = {}

        self.module_table = None

    def minimize(self):
        self.c.execute('''SELECT seed_name FROM key_lookup ORDER BY block_count DESC''')
        seeds = self.c.fetchall()

        for seed in seeds:
            seed_name = seed[0]

            self.c.execute('''SELECT block_count, traces FROM key_lookup WHERE seed_name = ?''', [seed_name])
            data = self.c.fetchone()

            block_count = data[0]
            trace_data = msgpack.unpackb(zlib.decompress(data[1]))

            # Save seed->block_count lookup
            self.master_bbcount[seed_name] = block_count

            print "[ +D+ ] - Merging %s with %s blocks into the master list." % (seed_name, block_count)

            for bblock, ins_count in trace_data.iteritems():
                if bblock not in self.master_bblock:
                    self.master_bblock[bblock] = seed_name
                    self.master_inscount[bblock] = ins_count

                # If basic_block exists and new trace has bigger ins_count, replace it
                elif self.master_inscount[bblock] < ins_count:
                    self.master_bblock[bblock] = seed_name
                    self.master_inscount[bblock] = ins_count

    def report(self):
        # Create results table
        block_results = sorted(set(self.master_bblock.itervalues()))
        for seed_name in block_results:
            self.c.execute('INSERT INTO results VALUES (?,?)', (seed_name, self.master_bbcount[seed_name]))
        self.sql.commit()

        self.c.execute('''SELECT * FROM results''')
        seed_results = self.c.fetchall()
        print "[ +D+ ] - Reduced set to %s covering %s unique blocks." % (len(block_results), len(self.master_bblock))

        self.c.execute('''SELECT * FROM results ORDER BY block_count DESC LIMIT 1;''')
        best_seed = self.c.fetchone()
        print "[ +D+ ] - Best seed %s covers %s unique blocks." % (best_seed[0], best_seed[1])

        with open(self.out, 'wb') as f:
            writer = csv.writer(f)
            writer.writerow(['Seed Name', 'Block Count'])
            writer.writerows(seed_results)
        print "[ +D+ ] - Wrote results to %s" % self.out

    def go(self):
        print "[ +D+ ] - Start minimizer."
        n1 = datetime.now()

        # Minimize traces
        self.minimize()

        # Update db and output to CSV
        self.report()

        n2 = datetime.now()
        print "[ +D+ ] - Reduction completed in %ss" % (n2 - n1).seconds

