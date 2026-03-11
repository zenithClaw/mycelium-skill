import argparse
import json
import sys
from sdk.mycelium_sdk import MyceliumClient

def get_client():
    # In production, this would read from env or config.
    # For now, hardcode to local dev server.
    return MyceliumClient(api_url="http://localhost:8001", agent_id="openclaw_local")

def main():
    parser = argparse.ArgumentParser(prog="mycelium_cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # seek
    seek_p = subparsers.add_parser("seek")
    seek_p.add_argument("--goal", required=True)
    seek_p.add_argument("--scope", choices=["task", "bug"], default="task")
    seek_p.add_argument("--tags", default="")

    # publish
    pub_p = subparsers.add_parser("publish")
    pub_p.add_argument("--goal", required=True)
    pub_p.add_argument("--scope", choices=["task", "bug"], default="task")
    pub_p.add_argument("--tags", default="")
    pub_p.add_argument("--path", required=True, help="JSON string of the path/steps")

    # feedback
    fb_p = subparsers.add_parser("feedback")
    fb_p.add_argument("--id", required=True)
    fb_p.add_argument("--result", choices=["success", "fail", "unknown"], required=True)

    args = parser.parse_args()

    try:
        from mycelium_sdk import MyceliumClient
        client = MyceliumClient(api_url="http://localhost:8001", agent_id="openclaw_local")

        if args.command == "seek":
            tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
            res = client.seek(goal=args.goal, scope=args.scope, tags=tags)
            print(json.dumps(res, indent=2, ensure_ascii=False))

        elif args.command == "publish":
            tags = [t.strip() for t in args.tags.split(",")] if args.tags else []
            path_obj = json.loads(args.path)
            ph_id = client.publish(goal=args.goal, scope=args.scope, tags=tags, path=path_obj)
            print(json.dumps({"status": "published", "id": ph_id}))

        elif args.command == "feedback":
            res = client.feedback(pheromone_id=args.id, result=args.result)
            print(json.dumps(res, indent=2))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()