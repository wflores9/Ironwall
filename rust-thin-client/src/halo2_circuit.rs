//! Minimal Halo2 speed-bound circuit stub (MockProver only).
use halo2_proofs::circuit::{Layouter, SimpleFloorPlanner};
use halo2_proofs::plonk::{Circuit, ConstraintSystem};
use halo2_proofs::arithmetic::Field;
use halo2curves::bn256::Fr as Fp;

#[derive(Clone, Debug)]
pub struct SpeedHalo2 {
    pub dx: Fp,
    pub dy: Fp,
    pub dz: Fp,
    pub max_speed: Fp,
    pub dt: Fp,
}

impl Circuit<Fp> for SpeedHalo2 {
    type Config = ();
    type FloorPlanner = SimpleFloorPlanner;

    fn without_witnesses(&self) -> Self {
        Self {
            dx: Fp::ZERO,
            dy: Fp::ZERO,
            dz: Fp::ZERO,
            max_speed: Fp::ZERO,
            dt: Fp::ONE,
        }
    }

    fn configure(meta: &mut ConstraintSystem<Fp>) -> Self::Config {
        let advice = meta.advice_column();
        let instance = meta.instance_column();
        meta.enable_equality(advice);
        meta.enable_equality(instance);
        ()
    }

    fn synthesize(
        &self,
        _config: Self::Config,
        _layouter: impl Layouter<Fp>,
    ) -> Result<(), halo2_proofs::plonk::Error> {
        // Stub: real constraints (dx²+dy²+dz² ≤ max²·dt²) come later
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use halo2_proofs::dev::MockProver;

    #[test]
    fn test_halo2_speed() {
        let circuit = SpeedHalo2 {
            dx: Fp::from(100u64),
            dy: Fp::from(0u64),
            dz: Fp::from(0u64),
            max_speed: Fp::from(1000u64),
            dt: Fp::from(100u64),
        };
        let prover = MockProver::run(8, &circuit, vec![]).expect("MockProver");
        assert_eq!(prover.verify(), Ok(()));
        println!("Halo2 speed circuit verified");
    }
}
