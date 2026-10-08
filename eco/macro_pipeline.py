"""Verified static publication, immutable inputs/records, and calendar integration."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re

from . import calendar as cal
from . import macro_assessment as engine
from .macro_adapter import normalize

ROOT=Path(__file__).resolve().parents[1]


def body(value):
    return engine.encode(value)+b"\n"


def read_json(path):
    return json.loads(path.read_bytes())


def write(path, value, immutable=False):
    content=body(value);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and immutable:
        if path.read_bytes()!=content:raise ValueError("immutable publication collision")
        return
    temp=path.with_name(path.name+".tmp")
    temp.write_bytes(content);os.replace(temp,path)


def read_asset(root, record):
    url=record.get("url","")
    if not re.fullmatch(r"/data/(?:calendar/releases/calendar-[a-f0-9]{20}/calendar|macro-assessment/(?:inputs/[a-f0-9]{64}|releases/macro-[a-f0-9]{20}/(?:assessment|manifest)))\.json",url):
        raise ValueError("invalid public asset path")
    path=root/"public"/url.lstrip("/")
    raw=path.read_bytes()
    if sha256(raw).hexdigest()!=record.get("sha256"):raise ValueError("public asset checksum mismatch")
    return json.loads(raw)


@contextmanager
def publication_lock(folder):
    folder.mkdir(parents=True,exist_ok=True)
    lock=folder/".publication.lock"
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise ValueError("macro publisher busy") from None
    try:yield
    finally:os.close(fd);lock.unlink()


def input_record(folder, value):
    content=body(value);sha=sha256(content).hexdigest()
    write(folder/"inputs"/(sha+".json"),value,True)
    return {"url":"/data/macro-assessment/inputs/"+sha+".json","sha256":sha}


def publish(root, bundle, calendar, batch_status, as_of, ruleset):
    original_status=batch_status
    root=Path(root);folder=root/"public/data/macro-assessment"
    with publication_lock(folder):
        pointer_path=folder/"latest.json"
        prior_pointer=read_json(pointer_path) if pointer_path.exists() else None
        previous=read_asset(root,prior_pointer) if prior_pointer else None
        manifest=read_asset(root,prior_pointer["manifest"]) if prior_pointer else None
        if previous and (previous["assessment_id"]!=prior_pointer["assessment_id"] or manifest["assessment_id"]!=previous["assessment_id"]):
            raise ValueError("previous assessment lineage mismatch")
        candidate=engine.assess(bundle,calendar,batch_status,as_of,previous,ruleset)
        if previous and candidate["assessment_id"]==previous["assessment_id"]:
            refresh_proof=input_record(folder,batch_status)
            write(folder/"status.json",{"outcome":"unchanged","checked_at":as_of,"assessment_id":previous["assessment_id"],
                                       "pipeline_state":candidate["pipeline_state"],"batch_status":refresh_proof,"last_successful_source_check_at":batch_status["data"].get("last_successful_source_check_at"),"last_good_retained":True})
            return {"outcome":"unchanged","assessment_id":previous["assessment_id"]}
        aid=candidate["assessment_id"];release=folder/"releases"/aid
        replay_manifest=None
        if (release/"assessment.json").exists():
            saved=read_json(release/"assessment.json")
            if engine.encode(engine.state_identity(saved))!=engine.encode(engine.state_identity(candidate)) or saved["previous_assessment_id"]!=candidate["previous_assessment_id"] or engine.utc(saved["as_of"])>engine.utc(as_of):
                raise ValueError("immutable assessment ID collision")
            candidate=saved
            if (release/"manifest.json").exists():
                replay_manifest=read_json(release/"manifest.json")
                if replay_manifest["state_sha256"]!=engine.digest(engine.state_identity(candidate)) or replay_manifest["assessment_sha256"]!=sha256((release/"assessment.json").read_bytes()).hexdigest():
                    raise ValueError("replay manifest mismatch")
                for name in ("observations","batch_status","ruleset"):
                    read_asset(root,replay_manifest[name])
            elif candidate["batch_status_sha256"]!=batch_status["sha256"]:
                # Recover a write interrupted between immutable artifact and
                # manifest. The original status proof was written first.
                proofs=[read_json(p) for p in (folder/"inputs").glob("*.json")]
                matches=[p for p in proofs if p.get("id")==candidate["batch_status_id"] and p.get("sha256")==candidate["batch_status_sha256"]]
                if len(matches)!=1:raise ValueError("missing original replay proof")
                batch_status=matches[0]
        bundle_record=input_record(folder,bundle)
        status_record=input_record(folder,batch_status)
        rules_record=input_record(folder,ruleset)
        write(release/"assessment.json",candidate,True)
        content=(release/"assessment.json").read_bytes();assessment_hash=sha256(content).hexdigest()
        manifest_data={"schema_version":engine.SCHEMA,"assessment_id":aid,"state_id":candidate["state_id"],
                       "assessment_sha256":assessment_hash,"state_sha256":engine.digest(engine.state_identity(candidate)),
                       "previous_assessment_id":candidate["previous_assessment_id"],"ruleset_version":engine.VERSION,
                       "ruleset_sha256":engine.digest(ruleset),"calendar":{"url":f'/data/calendar/releases/{calendar["release_id"]}/calendar.json',"sha256":bundle["calendar_sha256"]},
                       "observations":bundle_record,"batch_status":status_record,"ruleset":rules_record,
                       "history_mode":"latest_vintage_context","scope":"US_major_macro_conditional_research"}
        write(release/"manifest.json",replay_manifest or manifest_data,True)
        write(folder/"records"/(aid+".json"),{"assessment_id":aid,"published_at":candidate["generated_at"],"previous_assessment_id":candidate["previous_assessment_id"],"assessment_sha256":assessment_hash},True)
        url=f"/data/macro-assessment/releases/{aid}"
        # The lock is shared by all local writers; verify pointer again before replacing it.
        if (read_json(pointer_path) if pointer_path.exists() else None)!=prior_pointer:
            raise ValueError("predecessor changed during publication")
        pointer={"schema_version":engine.SCHEMA,"assessment_id":aid,"url":url+"/assessment.json","sha256":assessment_hash,
                 "calendar_release_id":calendar["release_id"],"ruleset_version":engine.VERSION,
                 "manifest":{"url":url+"/manifest.json","sha256":sha256((release/"manifest.json").read_bytes()).hexdigest()}}
        write(pointer_path,pointer)
        refresh_proof=input_record(folder,original_status)
        write(folder/"status.json",{"outcome":"published","checked_at":as_of,"assessment_id":aid,"pipeline_state":candidate["pipeline_state"],"batch_status":refresh_proof,"last_successful_source_check_at":original_status["data"].get("last_successful_source_check_at"),"last_good_retained":False})
        return {"outcome":"published","assessment_id":aid,"regime_id":candidate["regime_id"]}


def load_sources(root, calendar):
    sources={}
    snapshot=root/"data/raw/calendar"/calendar["private_backup"]["snapshot_id"]
    for key,expected in calendar["sources"].items():
        for path in (snapshot/(key+".json"),root/"data/raw/calendar/cache"/(key+".json")):
            if path.exists():
                data=read_json(path)
                if data.get("sha256")==expected["sha256"]:
                    sources[key]=data;break
    return sources


def run(root=ROOT, now=None):
    root=Path(root);now=now or datetime.now(timezone.utc);as_of=cal.stamp(now)
    folder=root/"public/data/macro-assessment"
    try:
        pointer=read_json(root/"public/data/calendar/latest.json")
        calendar=read_asset(root,pointer)
        config=read_json(root/"configs/macro/macro-cross-v1.0.1.json")
        old_pointer=read_json(folder/"latest.json") if (folder/"latest.json").exists() else None
        prior_manifest=read_asset(root,old_pointer["manifest"]) if old_pointer else None
        prior_bundle=read_asset(root,prior_manifest["observations"]) if prior_manifest else None
        sources=load_sources(root,calendar)
        # A source outage cannot erase a previously verified normalization of
        # the identical immutable parent. Freshness still gates the conclusion.
        if prior_bundle and prior_bundle["calendar_sha256"]==pointer["sha256"] and len(sources)<len(calendar["sources"]):
            bundle=prior_bundle
        else:
            bundle=normalize(calendar,pointer["sha256"],sources,config,as_of,prior_bundle)
        calendar_status=read_json(root/"public/data/calendar/status.json")
        last_success=calendar_status.get("last_success_at")
        if not last_success and prior_manifest:
            proofs=[read_asset(root,prior_manifest["batch_status"])]
            if (folder/"status.json").exists():
                prior_status=read_json(folder/"status.json")
                if prior_status.get("batch_status"):
                    proofs.append(read_asset(root,prior_status["batch_status"]))
            known=[p for p in proofs if engine.utc(p["data"]["known_at"])<=engine.utc(as_of) and p["sha256"]==engine.digest(p["data"])]
            if known:last_success=max(known,key=lambda p:engine.utc(p["data"]["known_at"]))["data"].get("last_successful_source_check_at")
        status_data={"known_at":as_of,"last_successful_source_check_at":last_success}
        status={"data":status_data,"sha256":engine.digest(status_data),"id":"macro-status-"+engine.digest(status_data)[:20]}
        return publish(root,bundle,calendar,status,as_of,config)
    except Exception:
        write(folder/"status.json",{"outcome":"error","checked_at":as_of,"last_good_retained":True})
        raise


if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Publish cross-indicator assessment of verified calendar")
    parser.add_argument("--root",type=Path,default=ROOT)
    args=parser.parse_args()
    print(json.dumps(run(args.root),ensure_ascii=False))
