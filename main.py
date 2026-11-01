"""CLI: python main.py <discover|enrich|filter|personalize|send|export|run-all>"""
import sys
import config, db, discovery, enrichment, filtering, personalize, sender, export

STAGES = {
    "discover": lambda c: discovery.discover(c),
    "enrich": enrichment.enrich_all,
    "filter": filtering.filter_all,
    "personalize": lambda c: personalize.personalize_all(c),
    "send": lambda c: (sender.send_emails(c), sender.queue_dms(c)),
    "export": export.export_all,
}

def main(argv):
    cmd = argv[1] if len(argv) > 1 else "run-all"
    conn = db.connect()
    order = list(STAGES) if cmd == "run-all" else [cmd]
    if any(s not in STAGES for s in order):
        sys.exit(__doc__)
    for s in order:
        print(f"\n=== {s} ===")
        STAGES[s](conn)

if __name__ == "__main__":
    main(sys.argv)
