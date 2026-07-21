use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IronwallConfig {
    pub player_id: String,
    pub hcs_topic_id: String,
    pub xrpl_account: String,
    pub tick_rate_hz: u32,
    pub max_speed_units_per_sec: f32,
}

impl Default for IronwallConfig {
    fn default() -> Self {
        Self {
            player_id: "player_001".to_string(),
            hcs_topic_id: "0.0.123456".to_string(),
            xrpl_account: "rIronwallAnchorXXXXXXXXXXXXXXXXXX".to_string(),
            tick_rate_hz: 60,
            max_speed_units_per_sec: 10.0,
        }
    }
}
