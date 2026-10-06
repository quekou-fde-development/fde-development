"""Canonical offline verification surface; delegates to the real production handler."""
import argparse
import json

import feedback


def process_feedback(run_dir):
    return feedback.verify_offline(run_dir)

STAGES = {'process_feedback': process_feedback}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=list(STAGES), required=True)
    parser.add_argument('--run-dir', required=True)
    args = parser.parse_args()
    result = STAGES[args.stage](args.run_dir)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
