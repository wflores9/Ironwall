use ironwall::recorder::MatchRecorder;
use std::fs;

#[test]
fn recorder_roundtrip() {
    let path = std::env::temp_dir().join("ironwall_test_match.tsv");
    let _ = fs::remove_file(&path);

    let rec = MatchRecorder::new(&path).expect("create");
    rec.record_attest("sess1", "p1", "quoteabc");
    rec.record_proof("sess1", "p1", "proof1", (0.,0.,0.), (0.1,0.,0.), 2.0, 50, "hash1");
    rec.record_challenge("sess1", "ch1");
    rec.record_heartbeat("sess1", (1., 2., 3.));
    assert_eq!(rec.count(), 4);

    let events = MatchRecorder::load(&path).expect("load");
    assert_eq!(events.len(), 4);
    assert_eq!(events[0].event_type, "attest");
    assert_eq!(events[1].event_type, "proof");
    assert_eq!(events[1].speed, 2.0);
    assert_eq!(events[3].to, (1., 2., 3.));

    let _ = fs::remove_file(&path);
}
