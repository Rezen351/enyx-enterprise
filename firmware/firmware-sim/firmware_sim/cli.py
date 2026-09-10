"""CLI for the firmware simulator.

Usage:
  python -m firmware_sim list
  python -m firmware_sim clone --node-id node-07 --mqtt-server tcp://mosquitto:1883
  python -m firmware_sim run   --node-id node-07
  python -m firmware_sim spawn --count 3 --mqtt-server tcp://mosquitto:1883
  python -m firmware_sim delete --node-id node-07
  python -m firmware_sim discover --node-id node-07
  python -m firmware_sim info  --node-id node-07
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading

from . import config
from .simulator import FirmwareSimulator


def _mqtt_args(args) -> dict:
    out = {}
    if args.mqtt_server:
        out["server"] = args.mqtt_server
    if args.mqtt_port:
        out["port"] = args.mqtt_port
    if args.mqtt_user is not None:
        out["user"] = args.mqtt_user
    if args.mqtt_pass is not None:
        out["pass"] = args.mqtt_pass
    return out


def cmd_list(_):
    items = config.list_instances()
    if not items:
        print("No instances cloned yet. Run: python -m firmware_sim clone")
        return
    for nid in items:
        cfg = config.load_instance(nid)
        paired = "paired" if cfg and cfg.paired else "unpaired"
        print(f"  {nid}  mac={cfg.mac if cfg else '?'}  {paired}  -> {cfg.mqtt['server'] if cfg else '?'}")


def cmd_clone(args):
    cfg = config.create_instance(node_id=args.node_id, mqtt_override=_mqtt_args(args))
    if args.rate:
        cfg.publish_rate_hz = args.rate
        config.save_instance(cfg)
    print(f"Cloned instance '{cfg.node_id}' (mac={cfg.mac}, fw={cfg.fw_version})")
    print(f"  config: {config.instance_path(cfg.node_id)}")
    print(f"  run it: python -m firmware_sim run --node-id {cfg.node_id}")


def cmd_run(args):
    cfg = config.load_instance(args.node_id)
    if not cfg:
        print(f"No instance '{args.node_id}'. Clone it first: python -m firmware_sim clone --node-id {args.node_id}",
              file=sys.stderr)
        sys.exit(1)
    if _mqtt_args(args):
        cfg.mqtt.update(_mqtt_args(args))
    FirmwareSimulator(cfg).run()


def cmd_spawn(args):
    mqtt_override = _mqtt_args(args)
    sims = []
    threads = []
    for _ in range(args.count):
        cfg = config.create_instance(mqtt_override=mqtt_override)
        if args.rate:
            cfg.publish_rate_hz = args.rate
            config.save_instance(cfg)
        sim = FirmwareSimulator(cfg)
        sims.append(sim)
        t = threading.Thread(target=sim.run, daemon=True)
        t.start()
        threads.append(t)
        print(f"  spawned {cfg.node_id} (mac={cfg.mac})")
    print(f"Running {args.count} clones. Ctrl+C to stop all.")
    try:
        while True:
            for t in threads:
                t.join(timeout=0.5)
            if not any(t.is_alive() for t in threads):
                break
    except KeyboardInterrupt:
        print("\nStopping all clones...")
        for s in sims:
            s.stop()


def cmd_delete(args):
    if config.delete_instance(args.node_id):
        print(f"Deleted instance '{args.node_id}'")
    else:
        print(f"No instance '{args.node_id}'")


def cmd_discover(args):
    cfg = config.load_instance(args.node_id)
    if not cfg:
        print(f"No instance '{args.node_id}'", file=sys.stderr)
        sys.exit(1)
    sim = FirmwareSimulator(cfg)
    sim.connect()
    import time
    time.sleep(1.0)
    sim.stop()
    print(f"Re-published discovery for {cfg.node_id}")


def cmd_info(args):
    cfg = config.load_instance(args.node_id)
    if not cfg:
        print(f"No instance '{args.node_id}'", file=sys.stderr)
        sys.exit(1)
    import json
    print(json.dumps(cfg.to_dict(), indent=2))


def cmd_inject(args):
    """Inject a command into a running device (output / input / emergency)."""
    import json
    import time

    import paho.mqtt.client as mqtt

    cfg = config.load_instance(args.node_id)
    if not cfg:
        print(f"No instance '{args.node_id}'", file=sys.stderr)
        sys.exit(1)

    m = cfg.mqtt
    host, port = FirmwareSimulator._parse_server(m["server"], m["port"])

    client = mqtt.Client()
    if m.get("user"):
        client.username_pw_set(m["user"], m.get("pass", ""))
    client.connect(host, port, 60)
    client.loop_start()

    prefix = "smartfarm"
    if args.kind == "output":
        topic = f"{prefix}/actuator/{args.node_id}"
        payload = {"action": "set_output", "target": args.target,
                   "value": args.value, "req_id": f"cli-{int(time.time())}"}
    elif args.kind == "emergency":
        topic = f"{prefix}/actuator/{args.node_id}"
        payload = {"action": "emergency_stop", "req_id": f"cli-{int(time.time())}"}
    elif args.kind == "input":
        topic = f"{prefix}/{args.node_id}/sim"
        payload = {"action": "set_input", "target": args.target, "value": args.value}
    else:
        print(f"Unknown kind '{args.kind}'", file=sys.stderr)
        sys.exit(2)

    client.publish(topic, json.dumps(payload), qos=1)
    print(f"Published to {topic}: {payload}")
    time.sleep(0.5)
    client.loop_stop()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="firmware_sim", description="ESP32 aeroponic-node firmware simulator over MQTT")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list", help="list cloned instances")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("clone", help="clone a new instance with a FIXED distinct id")
    sp.add_argument("--node-id", default=None, help="fixed node id (auto if omitted)")
    sp.add_argument("--mqtt-server", default=None)
    sp.add_argument("--mqtt-port", type=int, default=None)
    sp.add_argument("--mqtt-user", default=None)
    sp.add_argument("--mqtt-pass", default=None)
    sp.add_argument("--rate", type=float, default=None,
                    help="telemetry publish rate in Hz (sub-second); overrides publish_interval")
    sp.set_defaults(func=cmd_clone)

    sp = sub.add_parser("run", help="run a cloned instance (connect + telemetry loop)")
    sp.add_argument("--node-id", required=True)
    sp.add_argument("--mqtt-server", default=None)
    sp.add_argument("--mqtt-port", type=int, default=None)
    sp.add_argument("--mqtt-user", default=None)
    sp.add_argument("--mqtt-pass", default=None)
    sp.set_defaults(func=cmd_run)

    sp = sub.add_parser("spawn", help="clone + run N instances concurrently")
    sp.add_argument("--count", type=int, default=1)
    sp.add_argument("--mqtt-server", default=None)
    sp.add_argument("--mqtt-port", type=int, default=None)
    sp.add_argument("--mqtt-user", default=None)
    sp.add_argument("--mqtt-pass", default=None)
    sp.add_argument("--rate", type=float, default=None,
                    help="telemetry publish rate in Hz (sub-second); overrides publish_interval")
    sp.set_defaults(func=cmd_spawn)

    sp = sub.add_parser("delete", help="remove a cloned instance")
    sp.add_argument("--node-id", required=True)
    sp.set_defaults(func=cmd_delete)

    sp = sub.add_parser("discover", help="re-publish discovery for an instance")
    sp.add_argument("--node-id", required=True)
    sp.set_defaults(func=cmd_discover)

    sp = sub.add_parser("info", help="print instance config")
    sp.add_argument("--node-id", required=True)
    sp.set_defaults(func=cmd_info)

    sp = sub.add_parser("inject", help="inject a command into a running device")
    sp.add_argument("--node-id", required=True)
    sp.add_argument("--target", default=None, help="output/input name (e.g. relay_pump)")
    sp.add_argument("--value", type=float, default=0, help="value (0/1, 0..255, or engineering)")
    sp.add_argument("--kind", choices=["output", "input", "emergency"], default="output",
                    help="what to inject (default: output)")
    sp.set_defaults(func=cmd_inject)

    return p


def main(argv=None) -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
