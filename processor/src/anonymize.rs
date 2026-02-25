use blake3::Hasher;

// hashes a patient's ID using BLAKE3, returns first 16 hex chars
pub fn hash_id(id: &str) -> String {
    // hash an input all at once
    let mut hasher = Hasher::new();
    // convert id to bytes and feed into hasher
    hasher.update(id.as_bytes());
    // compute hash from fed bytes
    let hash = hasher.finalize();
    // raw 32-byte hash → 64-char hex → truncate to first 16 chars → owned String
    hash.to_hex()[..16].to_string()
}

// tests - compile this module when running 'cargo test'
#[cfg(test)]
mod tests {
    use super::*; // bring hash_id into scope

    #[test]
    fn same_id_gives_same_hash() {
        let id = "test_id";
        let hash = hash_id(id);
        assert_eq!(hash, hash_id(id));
    }

    #[test]
    fn diff_ids_give_diff_hashes() {
        let id1 = "test_id1";
        let id2 = "test_id2";
        assert_ne!(hash_id(id1), hash_id(id2));
    }

    #[test]
    fn hash_output_is_truncated() {
        let id = "test_id";
        let hash = hash_id(id);
        assert_eq!(hash.len(), 16);
    }
}
