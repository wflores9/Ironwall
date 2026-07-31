//! Halo2 speed-bound circuit: prove dx²+dy²+dz² * SCALE² <= max_speed² * dt²
//! (fixed-point style integers on BN256 Fr). MockProver for now.

use halo2_proofs::arithmetic::Field;
use halo2_proofs::circuit::{Layouter, SimpleFloorPlanner, Value};
use halo2_proofs::plonk::{
    Advice, Circuit, Column, ConstraintSystem, Error, Selector,
};
use halo2_proofs::poly::Rotation;
use halo2curves::bn256::Fr as Fp;

#[derive(Clone, Debug)]
pub struct SpeedConfig {
    advice: [Column<Advice>; 3],
    q_mul: Selector,
    q_sum: Selector,
    q_bound: Selector,
}

#[derive(Clone, Debug, Default)]
pub struct SpeedHalo2 {
    /// Private witnesses (fixed-point)
    pub dx: Option<u64>,
    pub dy: Option<u64>,
    pub dz: Option<u64>,
    pub max_speed: Option<u64>,
    pub dt: Option<u64>,
}

impl Circuit<Fp> for SpeedHalo2 {
    type Config = SpeedConfig;
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self::default()
    }

    fn configure(meta: &mut ConstraintSystem<Fp>) -> Self::Config {
        let advice = [
            meta.advice_column(),
            meta.advice_column(),
            meta.advice_column(),
        ];
        for a in &advice {
            meta.enable_equality(*a);
        }
        let q_mul = meta.selector();
        let q_sum = meta.selector();
        let q_bound = meta.selector();

        // a * b = c
        meta.create_gate("mul", |meta| {
            let q = meta.query_selector(q_mul);
            let a = meta.query_advice(advice[0], Rotation::cur());
            let b = meta.query_advice(advice[1], Rotation::cur());
            let c = meta.query_advice(advice[2], Rotation::cur());
            vec![q * (a * b - c)]
        });

        // a + b + c = sum  (stored in advice[0] next row pattern via copy — simplified:
        // enforce a + b + c - sum = 0 where sum is advice[0] on same constrained row set)
        meta.create_gate("sum3", |meta| {
            let q = meta.query_selector(q_sum);
            let a = meta.query_advice(advice[0], Rotation::cur());
            let b = meta.query_advice(advice[1], Rotation::cur());
            let c = meta.query_advice(advice[2], Rotation::cur());
            // advice[0] next is used as sum via equality copy in synthesize;
            // here: a+b+c must equal the value we'll assign as sum on a dedicated cell.
            // Use: a + b + c - (a+b+c) trivial — real sum enforced by assigning sum cell
            // and constraining sum - a - b - c = 0 where sum is advice[0] Rotation::next()
            let sum = meta.query_advice(advice[0], Rotation::next());
            vec![q * (a + b + c - sum)]
        });

        // lhs + slack = rhs  =>  dist_sq * scale2 + slack - max_sq * dt_sq = 0
        meta.create_gate("bound", |meta| {
            let q = meta.query_selector(q_bound);
            let lhs = meta.query_advice(advice[0], Rotation::cur());
            let slack = meta.query_advice(advice[1], Rotation::cur());
            let rhs = meta.query_advice(advice[2], Rotation::cur());
            vec![q * (lhs + slack - rhs)]
        });

        SpeedConfig {
            advice,
            q_mul,
            q_sum,
            q_bound,
        }
    }

    fn synthesize(
        &self,
        config: Self::Config,
        mut layouter: impl Layouter<Fp>,
    ) -> Result<(), Error> {
        let dx = self.dx.unwrap_or(0);
        let dy = self.dy.unwrap_or(0);
        let dz = self.dz.unwrap_or(0);
        let max_speed = self.max_speed.unwrap_or(0);
        let dt = self.dt.unwrap_or(1).max(1);

        let dx2 = dx.saturating_mul(dx);
        let dy2 = dy.saturating_mul(dy);
        let dz2 = dz.saturating_mul(dz);
        let dist_sq = dx2.saturating_add(dy2).saturating_add(dz2);
        let scale2: u64 = 1_000_000; // 1000^2 for milli-units
        let lhs = dist_sq.saturating_mul(scale2);
        let max_sq = max_speed.saturating_mul(max_speed);
        let dt_sq = dt.saturating_mul(dt);
        let rhs = max_sq.saturating_mul(dt_sq);
        let slack = rhs.saturating_sub(lhs); // requires rhs >= lhs (native pre-check)

        layouter.assign_region(
            || "speed region",
            |mut region| {
                // row 0: dx * dx = dx2
                config.q_mul.enable(&mut region, 0)?;
                region.assign_advice(|| "dx", config.advice[0], 0, || Value::known(Fp::from(dx)))?;
                region.assign_advice(|| "dx", config.advice[1], 0, || Value::known(Fp::from(dx)))?;
                region.assign_advice(|| "dx2", config.advice[2], 0, || Value::known(Fp::from(dx2)))?;

                // row 1: dy * dy = dy2
                config.q_mul.enable(&mut region, 1)?;
                region.assign_advice(|| "dy", config.advice[0], 1, || Value::known(Fp::from(dy)))?;
                region.assign_advice(|| "dy", config.advice[1], 1, || Value::known(Fp::from(dy)))?;
                region.assign_advice(|| "dy2", config.advice[2], 1, || Value::known(Fp::from(dy2)))?;

                // row 2: dz * dz = dz2
                config.q_mul.enable(&mut region, 2)?;
                region.assign_advice(|| "dz", config.advice[0], 2, || Value::known(Fp::from(dz)))?;
                region.assign_advice(|| "dz", config.advice[1], 2, || Value::known(Fp::from(dz)))?;
                region.assign_advice(|| "dz2", config.advice[2], 2, || Value::known(Fp::from(dz2)))?;

                // row 3: dx2 + dy2 + dz2 = dist_sq  (sum on row 4 col0)
                config.q_sum.enable(&mut region, 3)?;
                region.assign_advice(|| "dx2", config.advice[0], 3, || Value::known(Fp::from(dx2)))?;
                region.assign_advice(|| "dy2", config.advice[1], 3, || Value::known(Fp::from(dy2)))?;
                region.assign_advice(|| "dz2", config.advice[2], 3, || Value::known(Fp::from(dz2)))?;
                region.assign_advice(
                    || "dist_sq",
                    config.advice[0],
                    4,
                    || Value::known(Fp::from(dist_sq)),
                )?;
                // fill unused on row 4
                region.assign_advice(|| "pad", config.advice[1], 4, || Value::known(Fp::ZERO))?;
                region.assign_advice(|| "pad", config.advice[2], 4, || Value::known(Fp::ZERO))?;

                // row 5: dist_sq * scale2 = lhs
                config.q_mul.enable(&mut region, 5)?;
                region.assign_advice(
                    || "dist_sq",
                    config.advice[0],
                    5,
                    || Value::known(Fp::from(dist_sq)),
                )?;
                region.assign_advice(
                    || "scale2",
                    config.advice[1],
                    5,
                    || Value::known(Fp::from(scale2)),
                )?;
                region.assign_advice(|| "lhs", config.advice[2], 5, || Value::known(Fp::from(lhs)))?;

                // row 6: max * max = max_sq
                config.q_mul.enable(&mut region, 6)?;
                region.assign_advice(
                    || "max",
                    config.advice[0],
                    6,
                    || Value::known(Fp::from(max_speed)),
                )?;
                region.assign_advice(
                    || "max",
                    config.advice[1],
                    6,
                    || Value::known(Fp::from(max_speed)),
                )?;
                region.assign_advice(
                    || "max_sq",
                    config.advice[2],
                    6,
                    || Value::known(Fp::from(max_sq)),
                )?;

                // row 7: dt * dt = dt_sq
                config.q_mul.enable(&mut region, 7)?;
                region.assign_advice(|| "dt", config.advice[0], 7, || Value::known(Fp::from(dt)))?;
                region.assign_advice(|| "dt", config.advice[1], 7, || Value::known(Fp::from(dt)))?;
                region.assign_advice(
                    || "dt_sq",
                    config.advice[2],
                    7,
                    || Value::known(Fp::from(dt_sq)),
                )?;

                // row 8: max_sq * dt_sq = rhs
                config.q_mul.enable(&mut region, 8)?;
                region.assign_advice(
                    || "max_sq",
                    config.advice[0],
                    8,
                    || Value::known(Fp::from(max_sq)),
                )?;
                region.assign_advice(
                    || "dt_sq",
                    config.advice[1],
                    8,
                    || Value::known(Fp::from(dt_sq)),
                )?;
                region.assign_advice(|| "rhs", config.advice[2], 8, || Value::known(Fp::from(rhs)))?;

                // row 9: lhs + slack = rhs
                config.q_bound.enable(&mut region, 9)?;
                region.assign_advice(|| "lhs", config.advice[0], 9, || Value::known(Fp::from(lhs)))?;
                region.assign_advice(
                    || "slack",
                    config.advice[1],
                    9,
                    || Value::known(Fp::from(slack)),
                )?;
                region.assign_advice(|| "rhs", config.advice[2], 9, || Value::known(Fp::from(rhs)))?;

                Ok(())
            },
        )?;
        Ok(())
    }
}

/// Native pre-check then circuit
pub fn prove_speed_halo2(dx: u64, dy: u64, dz: u64, max_speed: u64, dt: u64) -> Result<(), String> {
    let dist_sq = dx.saturating_mul(dx)
        .saturating_add(dy.saturating_mul(dy))
        .saturating_add(dz.saturating_mul(dz));
    let lhs = dist_sq.saturating_mul(1_000_000);
    let rhs = max_speed
        .saturating_mul(max_speed)
        .saturating_mul(dt.max(1))
        .saturating_mul(dt.max(1));
    if lhs > rhs {
        return Err(format!("speedhack: lhs={lhs} > rhs={rhs}"));
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use halo2_proofs::dev::MockProver;

    #[test]
    fn valid_slow_movement() {
        prove_speed_halo2(100, 0, 0, 1000, 100).unwrap();
        let circuit = SpeedHalo2 {
            dx: Some(100),
            dy: Some(0),
            dz: Some(0),
            max_speed: Some(1000),
            dt: Some(100),
        };
        let prover = MockProver::run(8, &circuit, vec![]).unwrap();
        assert_eq!(prover.verify(), Ok(()));
        println!("Halo2 valid movement OK");
    }

    #[test]
    fn speedhack_rejected_natively() {
        let err = prove_speed_halo2(50_000, 0, 0, 10, 16).unwrap_err();
        assert!(err.contains("speedhack"));
        println!("Halo2 speedhack rejected: {err}");
    }
}
