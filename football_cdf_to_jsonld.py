import argparse
import json
import numbers
import re
import urllib.parse as url
from pathlib import Path

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, XSD, OWL, RDFS

CORE = Namespace("https://w3id.org/football-cdf/core#")


def core(local: str) -> URIRef:
    return CORE[local]


def slug(text: str) -> str:
    return url.quote(str(text).lower().replace(" ", "_"), safe="_")


def lit(v, dt=None):
    if v is None:
        return None
    if dt:
        return Literal(v, datatype=dt)
    if isinstance(v, bool):
        return Literal(v, datatype=XSD.boolean)
    if isinstance(v, numbers.Integral):
        return Literal(int(v), datatype=XSD.integer)
    if isinstance(v, numbers.Real):
        return Literal(float(v), datatype=XSD.float)
    if isinstance(v, str) and v.endswith("Z") and "T" in v:
        return Literal(v, datatype=XSD.dateTime)
    return Literal(v, datatype=XSD.string)


def add(g: Graph, s, p, v, dt=None):
    if v is not None:
        g.add((s, p, lit(v, dt)))


def norm_token(s) -> str | None:
    if s is None:
        return None
    t = str(s).strip().lower()
    t = t.replace(" ", "_").replace("-", "_")
    t = t.replace("*", "")
    t = re.sub(r"[^a-z0-9_]+", "_", t)
    t = re.sub(r"_+", "_", t).strip("_")
    return t or None


def body_part_ontology(raw) -> str | None:
    n = norm_token(raw)
    if not n:
        return None
    if n in ("right_foot", "left_foot", "head", "other"):
        return n
    if "right" in n and "foot" in n:
        return "right_foot"
    if "left" in n and "foot" in n:
        return "left_foot"
    if n == "head" or "head" in n:
        return "head"
    return "other"


PASS_OUTCOMES = frozenset({"successful", "out_of_play", "intercepted"})
SHOT_OUTCOMES = frozenset({"successful", "saved", "blocked", "wide", "woodwork", "own_goal"})
PASS_TYPES = frozenset({"none", "throw_in", "free_kick", "corner_kick", "goal_kick", "kick_off"})
SHOT_TYPES = frozenset({"none", "penalty_kick", "free_kick", "corner_kick"})


def pass_outcome_from_event(ev) -> str | None:
    raw = ev.get("event_outcome_type")
    o = norm_token(raw) if raw else None
    if o in PASS_OUTCOMES:
        return o
    if raw == "Out" or o == "out":
        return "out_of_play"
    if o == "intercepted":
        return "intercepted"
    if ev.get("event_type") == "pass":
        if ev.get("event_is_successful") is True and o not in ("incomplete", "out_of_play", "intercepted"):
            if o is None or o == "":
                return "successful"
        if o == "incomplete":
            return None
    return None


def shot_outcome_from_event(ev, is_goal: bool) -> str | None:
    if is_goal:
        return "successful"
    o = norm_token(ev.get("event_outcome_type"))
    if o in SHOT_OUTCOMES:
        return o
    if o == "goal":
        return "successful"
    return None


def pass_type_from_subtype(sub) -> str | None:
    n = norm_token(sub)
    if not n:
        return None
    if n in PASS_TYPES:
        return n
    if "throw" in n:
        return "throw_in"
    if "corner" in n:
        return "corner_kick"
    if "goal_kick" in n or n == "goal_kick":
        return "goal_kick"
    if "kick_off" in n or n == "kickoff" or n == "kick_off":
        return "kick_off"
    if "free_kick" in n or (n.startswith("free") and "kick" in n):
        return "free_kick"
    return None


def shot_type_from_subtype(sub) -> str | None:
    n = norm_token(sub)
    if not n:
        return None
    if n in SHOT_TYPES:
        return n
    if "penalty" in n:
        return "penalty_kick"
    if "corner" in n:
        return "corner_kick"
    if "free" in n and "kick" in n:
        return "free_kick"
    return None


def bind_graph_prefixes(g: Graph, include_ontology_prefixes: bool = False):
    g.bind("", CORE)
    g.bind("xsd", XSD)
    g.bind("owl", OWL)
    g.bind("rdfs", RDFS)
    if include_ontology_prefixes:
        g.bind("dcterms", Namespace("http://purl.org/dc/terms/"))
        g.bind("vann", Namespace("http://purl.org/vocab/vann/"))


def build_graph(sheet_fp, events_fp, meta_fp) -> Graph:
    with open(sheet_fp, encoding="utf-8") as f:
        sheet = json.load(f)
    with open(events_fp, encoding="utf-8") as f:
        events = json.load(f)
    with open(meta_fp, encoding="utf-8") as f:
        meta = json.load(f)

    g = Graph()
    bind_graph_prefixes(g)

    mid = str(meta["match_id"])
    m_uri = core(f"match/{mid}")
    g.add((m_uri, RDF.type, core("Match")))
    add(g, m_uri, core("id"), mid)

    comp = meta["competition"]
    comp_id = comp["competition_id"]
    comp_name = comp.get("competition_name")

    c_uri = core(f"competition/{comp_id}")
    g.add((c_uri, RDF.type, core("Competition")))
    add(g, c_uri, core("id"), comp_id)
    add(g, c_uri, RDFS.label, comp_name)
    g.add((m_uri, core("competition"), c_uri))

    season_id = meta.get("season_id")
    if season_id is not None:
        s_uri = core(f"season/{season_id}")
        g.add((s_uri, RDF.type, core("Season")))
        add(g, s_uri, core("id"), season_id)
        g.add((m_uri, core("season"), s_uri))

    add(
        g,
        m_uri,
        core("kickoff_time"),
        meta.get("match_kickoff_time") or meta.get("match kickoff time"),
    )

    status = sheet["match"]["status"]
    st_uri = core(f"match_status/{mid}")
    g.add((st_uri, RDF.type, core("Match_Status")))
    g.add((m_uri, core("match_status"), st_uri))
    for src_key in ("is_neutral", "has_extratime", "has_shootout"):
        val = status.get(src_key) or status.get(src_key.replace("_", " "))
        add(g, st_uri, core(src_key), val)

    for period, val in sheet["match"]["result"].items():
        if period == "final winning team id":
            continue
        r_uri = core(f"match_result/{mid}/{slug(period)}")
        g.add((r_uri, RDF.type, core("Match_Result")))
        g.add((m_uri, core("match_result"), r_uri))
        add(g, r_uri, core("result_period"), period)
        add(g, r_uri, core("result_home"), val.get("home"), XSD.integer)
        add(g, r_uri, core("result_away"), val.get("away"), XSD.integer)

    if meta.get("referee"):
        ref = meta["referee"]
        r_uri = core(f"referee/{ref.get('id', 'unknown')}")
        g.add((r_uri, RDF.type, core("Referee")))
        add(g, r_uri, core("id"), ref.get("id"))
        add(g, r_uri, core("name"), ref.get("name"))
        g.add((m_uri, core("referee"), r_uri))

    id2player = {}
    for side in ("home", "away"):
        t = sheet["teams"][side]
        t_uri = core(f"team/{t['id']}")
        g.add((t_uri, RDF.type, core("Team")))
        add(g, t_uri, core("id"), t["id"])
        add(g, t_uri, RDFS.label, t["name"])
        g.add((m_uri, core(f"teams_{side}"), t_uri))

        for p in t["players"]:
            p_uri = core(f"player/{p['id']}")
            id2player[str(p["id"])] = p_uri
            g.add((p_uri, RDF.type, core("Player")))
            g.add((t_uri, core("players"), p_uri))

            first = p.get("first_name")
            last = p.get("last_name")
            pname = p.get("player_name") or " ".join(x for x in [first, last] if x)

            add(g, p_uri, core("id"), p["id"])
            add(g, p_uri, RDFS.label, pname)
            add(g, p_uri, core("jersey_number"), p.get("jersey_number"), XSD.integer)
            add(g, p_uri, core("is_starter"), p.get("is_starter"))
            add(g, p_uri, core("has_played"), p.get("has_played"))
            g.add((p_uri, core("team_id"), t_uri))

    for wi, w in enumerate(meta.get("match", {}).get("whistles") or []):
        w_uri = core(f"whistle/{mid}/{wi}_{slug(w['time'])}")
        g.add((w_uri, RDF.type, core("Whistle")))
        g.add((w_uri, RDF.type, core("Event")))
        g.add((m_uri, core("events"), w_uri))
        wt = norm_token(w.get("type")) or str(w.get("type") or "").lower().replace(" ", "_")
        add(g, w_uri, core("whistle_type"), wt)
        wst = w.get("sub_type")
        if wst is not None:
            add(g, w_uri, core("whistle_outcome_type"), norm_token(wst) or wst)
        add(g, w_uri, core("time"), w["time"])
        add(g, w_uri, core("id"), f"{mid}-whistle-{wi}")

    goal_lkp = {
        (g0["time"], str(g0["player_id"]), str(g0["team_id"])): g0
        for g0 in sheet["events"]["goals"]
    }
    sub_lkp = {s["in_time"]: s for s in sheet["events"]["substitutions"]}
    card_lkp = {(c["time"], str(c["player_id"])): c for c in sheet["events"]["cards"]}

    event_id_uri = {str(ev["event_id"]): core(f"event/{ev['event_id']}") for ev in events}

    for ev in events:
        e_uri = event_id_uri[str(ev["event_id"])]
        g.add((e_uri, RDF.type, core("Event")))
        g.add((m_uri, core("events"), e_uri))

        etype_raw = (ev.get("event_type") or "").lower()
        etype_norm = norm_token(ev.get("event_type")) or etype_raw.replace(" ", "_")

        ot_raw = ev.get("event_outcome_type")
        ot_lit = norm_token(ot_raw) if ot_raw else ot_raw
        sub_raw = ev.get("event_sub_type")
        sub_lit = norm_token(sub_raw) if sub_raw else sub_raw

        add(g, e_uri, core("id"), ev["event_id"])
        add(g, e_uri, core("time"), ev["event_time"])
        add(g, e_uri, core("event_period"), ev["event_period"].replace(" ", "_"))
        add(g, e_uri, core("type"), etype_norm)
        add(g, e_uri, core("sub_type"), sub_lit)
        add(g, e_uri, core("outcome_type"), ot_lit)
        add(g, e_uri, core("x"), ev["event_x"], XSD.float)
        add(g, e_uri, core("y"), ev["event_y"], XSD.float)
        add(g, e_uri, core("x_end"), ev["event_x_end"], XSD.float)
        add(g, e_uri, core("y_end"), ev["event_y_end"], XSD.float)
        add(g, e_uri, core("body_part"), body_part_ontology(ev.get("event_body_part")))

        if ev.get("event_player_id"):
            g.add((e_uri, core("player_id"), id2player[str(ev["event_player_id"])]))
        g.add((e_uri, core("team_id"), core(f"team/{ev['event_team_id']}")))

        for rid in ev.get("event_related_event_ids") or []:
            rid_s = str(rid)
            target = event_id_uri.get(rid_s, core(f"event/{rid_s}"))
            g.add((e_uri, core("related_event_ids"), target))

        outcome_lower = (ev.get("event_outcome_type") or "").lower()

        if etype_raw == "shot":
            g.add((e_uri, RDF.type, core("Shot")))
            is_goal = outcome_lower in {"goal", "successful"}
            if is_goal:
                g.add((e_uri, RDF.type, core("Goal")))
                g.add((m_uri, core("events_goals"), e_uri))
                key = (
                    ev["event_time"],
                    str(ev["event_player_id"]),
                    str(ev["event_team_id"]),
                )
                gd = goal_lkp.get(key)
                if gd:
                    if gd.get("assist_id"):
                        g.add(
                            (e_uri, core("assist_id"), id2player[str(gd["assist_id"])])
                        )
                    add(g, e_uri, core("is_own_goal"), gd.get("is_own_goal"))
                    add(g, e_uri, core("is_penalty"), gd.get("is_penalty"))

            so = shot_outcome_from_event(ev, is_goal)
            if so:
                add(g, e_uri, core("shot_outcome_type"), so)
            stp = shot_type_from_subtype(ev.get("event_sub_type"))
            if stp:
                add(g, e_uri, core("shot_type"), stp)

        elif etype_raw == "pass":
            g.add((e_uri, RDF.type, core("Pass")))
            rid = ev.get("event_receiver_id")
            if rid:
                recv = id2player.get(str(rid), core(f"player/{rid}"))
                g.add((e_uri, core("receiver_id"), recv))
            add(g, e_uri, core("receiver_time"), ev.get("event_receiver_time"))
            po = pass_outcome_from_event(ev)
            if po:
                add(g, e_uri, core("pass_outcome_type"), po)
            pt = pass_type_from_subtype(ev.get("event_sub_type"))
            if pt:
                add(g, e_uri, core("pass_type"), pt)

        elif etype_raw == "substitution":
            g.add((e_uri, RDF.type, core("Subtitution")))
            g.add((e_uri, RDF.type, core("Whistle")))
            sd = sub_lkp.get(ev["event_time"])
            if sd:
                g.add((e_uri, core("out_player_id"), id2player[str(sd["out_player_id"])]))
                add(g, e_uri, core("out_time"), sd["out_time"])
            g.add((m_uri, core("events_subtitutions"), e_uri))

        else:
            ck = (ev["event_time"], str(ev.get("event_player_id") or ""))
            cinfo = card_lkp.get(ck)
            if etype_raw == "card" or cinfo:
                g.add((e_uri, RDF.type, core("Card")))
                g.add((e_uri, RDF.type, core("Whistle")))
                ctype = (cinfo or {}).get("type")
                add(g, e_uri, core("card_type"), ctype)
                g.add((m_uri, core("events_cards"), e_uri))
            else:
                g.add((e_uri, RDF.type, core("Misc")))
                add(g, e_uri, core("misc_type"), etype_norm)
                mo = None
                if ev.get("event_is_successful") is True:
                    mo = "successful"
                elif ev.get("event_is_successful") is False:
                    mo = "unsuccessful"
                if mo:
                    add(g, e_uri, core("misc_outcome_type"), mo)

    meta_uri = core(f"meta/{mid}")
    g.add((meta_uri, RDF.type, core("Meta")))
    add(g, meta_uri, core("version"), "0.1.0")
    add(g, meta_uri, core("vendor"), "StatsBomb")
    inner = meta.get("meta") or {}
    add(g, meta_uri, core("fps"), inner.get("fps"), XSD.integer)
    add(g, meta_uri, core("collection_timing"), inner.get("collection_timing"))
    g.add((m_uri, core("meta_video"), meta_uri))

    return g


def serialize_graph(
    g: Graph, out_path: Path, fmt: str, include_ontology_prefixes: bool = False
):
    bind_graph_prefixes(g, include_ontology_prefixes=include_ontology_prefixes)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "turtle":
        g.serialize(destination=out_path, format="turtle")
    else:
        context = {"@vocab": str(CORE), "xsd": str(XSD)}
        g.serialize(
            destination=out_path, format="json-ld", context=context, indent=2
        )


def try_build_graph(match_dir: Path) -> Graph | None:
    sheet = match_dir / "match_sheet_cdf.json"
    events = match_dir / "event_cdf.json"
    meta = match_dir / "match_meta_cdf.json"
    if not (sheet.exists() and events.exists() and meta.exists()):
        print(f"Missing CDF files in {match_dir}")
        return None
    return build_graph(sheet, events, meta)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet")
    ap.add_argument("--events")
    ap.add_argument("--meta")
    ap.add_argument("--out", default="out/match.jsonld")
    ap.add_argument(
        "--format",
        choices=("json-ld", "turtle"),
        default="json-ld",
        help="Serialization for single-match mode",
    )
    ap.add_argument("--root", help="Dir containing per-match CDF folders")
    ap.add_argument(
        "--out-ttl",
        help="Single Turtle output for batch mode (merged ABox)",
    )
    ap.add_argument(
        "--ontology",
        type=Path,
        help="Turtle ontology to merge into batch output (default: ontology.ttl next to this script)",
    )
    ap.add_argument(
        "--no-with-ontology",
        action="store_true",
        help="Batch: do not merge ontology TBox into --out-ttl",
    )
    args = ap.parse_args()

    if args.root:
        if not args.out_ttl:
            ap.error("Batch mode requires --out-ttl")
        root = Path(args.root)
        script_dir = Path(__file__).resolve().parent
        onto_path = args.ontology
        if onto_path is None and not args.no_with_ontology:
            default_onto = script_dir / "ontology.ttl"
            if default_onto.exists():
                onto_path = default_onto
            else:
                onto_path = None

        g_all = Graph()
        if onto_path and not args.no_with_ontology:
            g_all.parse(onto_path, format="turtle")
        n = 0
        for match_dir in sorted(root.iterdir(), key=lambda p: p.name):
            if not match_dir.is_dir():
                continue
            g = try_build_graph(match_dir)
            if g is not None:
                g_all += g
                n += 1
        serialize_graph(
            g_all,
            Path(args.out_ttl),
            "turtle",
            include_ontology_prefixes=bool(onto_path and not args.no_with_ontology),
        )
        print(f"Turtle KG written -> {args.out_ttl} ({n} matches)")
    else:
        if not (args.sheet and args.events and args.meta):
            ap.error("Single mode needs --sheet --events --meta")
        g = build_graph(args.sheet, args.events, args.meta)
        out_f = Path(args.out)
        fmt = args.format
        if fmt == "json-ld" and out_f.suffix.lower() in (".ttl", ".turtle"):
            fmt = "turtle"
        serialize_graph(g, out_f, fmt)
        print(f"Written ({fmt}) -> {out_f}")
