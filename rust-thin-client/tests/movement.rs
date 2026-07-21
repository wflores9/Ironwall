use ironwall::zk::ZkMovementValidator;

#[tokio::test]
async fn valid_slow_movement_passes() {
    let zk = ZkMovementValidator::new(10.0);
    let proof = zk
        .prove_valid_movement("p1", (0.0, 0.0, 0.0), (0.1, 0.0, 0.0), 50)
        .await
        .expect("should pass");
    assert!(proof.speed < 10.0);
}

#[tokio::test]
async fn speedhack_is_rejected() {
    let zk = ZkMovementValidator::new(10.0);
    let err = zk
        .prove_valid_movement("p1", (0.0, 0.0, 0.0), (100.0, 0.0, 0.0), 16)
        .await
        .expect_err("should reject");
    assert!(matches!(err, ironwall::IronwallError::InvalidMovement(_)));
}
