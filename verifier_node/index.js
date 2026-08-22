const crypto = require('crypto');
const nacl = require('tweetnacl');
const canonicalJson = require('canonical-json');

function sha256(data) {
    return crypto.createHash('sha256').update(data).digest();
}

function sha256Hex(data) {
    return crypto.createHash('sha256').update(data).digest('hex');
}

function canonicalize(data) {
    return Buffer.from(canonicalJson(data));
}

function leafHash(entry) {
    return sha256(Buffer.concat([Buffer.from([0x00]), entry]));
}

function nodeHash(left, right) {
    return sha256(Buffer.concat([Buffer.from([0x01]), left, right]));
}

function verifyInclusion(fn, sn, leafData, path, expectedRoot) {
    let computed = leafHash(leafData);
    for (const sibling of path) {
        if (sn === 0) return false;
        if ((fn & 1) || fn === sn) {
            computed = nodeHash(sibling, computed);
            if (!(fn & 1)) {
                while (fn && !(fn & 1)) {
                    fn >>= 1;
                    sn >>= 1;
                }
            }
        } else {
            computed = nodeHash(computed, sibling);
        }
        fn >>= 1;
        sn >>= 1;
    }
    return sn === 0 && computed.equals(expectedRoot);
}

function verifySignature(publicKeyB64, payload, signatureB64) {
    try {
        const publicKey = Buffer.from(publicKeyB64, 'base64');
        const signature = Buffer.from(signatureB64, 'base64');
        const message = canonicalize(payload);
        return nacl.sign.detached.verify(
            new Uint8Array(message),
            new Uint8Array(signature),
            new Uint8Array(publicKey)
        );
    } catch (e) {
        return false;
    }
}

function verifyManifest(manifest) {
    const signatureObj = manifest.signature;
    if (!signatureObj || signatureObj.algorithm !== 'Ed25519') {
        return { signature_valid: false, overall: false };
    }
    const unsignedManifest = JSON.parse(JSON.stringify(manifest));
    const signatureValue = unsignedManifest.signature.value;
    delete unsignedManifest.signature;
    const pubKey = manifest.observer.public_key;
    const isValid = verifySignature(pubKey, unsignedManifest, signatureValue);
    return {
        signature_valid: isValid,
        overall: isValid
    };
}

function verifyObservation(manifest, proof) {
    const sigResult = verifyManifest(manifest);
    try {
        const entry = proof.entry;
        const checkpoint = proof.checkpoint;
        if (entry.observation_id !== manifest.observation_id) {
            return { ...sigResult, merkle_valid: false, overall: false };
        }
        const manifestHash = 'sha256:' + sha256Hex(canonicalize(manifest));
        if (entry.manifest_hash !== manifestHash) {
            return { ...sigResult, merkle_valid: false, overall: false };
        }
        const unsignedCheckpoint = JSON.parse(JSON.stringify(checkpoint));
        const checkpointSig = unsignedCheckpoint.signature;
        delete unsignedCheckpoint.signature;
        const checkpointSigValid = verifySignature(
            checkpoint.log_public_key, 
            unsignedCheckpoint, 
            checkpointSig
        );
        if (!checkpointSigValid) {
            return { ...sigResult, merkle_valid: false, overall: false };
        }
        const path = proof.inclusion_path.map(item => Buffer.from(item.split(':')[1], 'hex'));
        const expectedRoot = Buffer.from(checkpoint.root_hash.split(':')[1], 'hex');
        const entryBytes = canonicalize({
            observation_id: entry.observation_id,
            manifest_hash: entry.manifest_hash
        });
        const merkleValid = verifyInclusion(
            entry.leaf_index,
            checkpoint.tree_size,
            entryBytes,
            path,
            expectedRoot
        );
        return {
            signature_valid: sigResult.signature_valid,
            merkle_valid: merkleValid,
            overall: sigResult.signature_valid && merkleValid
        };
    } catch (e) {
        return { ...sigResult, merkle_valid: false, overall: false };
    }
}

module.exports = {
    verifyManifest,
    verifyObservation
};
