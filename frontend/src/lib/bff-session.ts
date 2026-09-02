import {
  createCipheriv,
  createDecipheriv,
  createHash,
  randomBytes,
} from "node:crypto";

export interface BffSession {
  accessToken: string;
  refreshToken: string;
}

const COOKIE_NAME = "invoiai_bff_session";
const VERSION = "v1";

function getKey(): Buffer {
  const secret = process.env.BFF_SESSION_SECRET;

  if (!secret || secret.length < 32) {
    throw new Error(
      "BFF_SESSION_SECRET must be configured and contain at least 32 characters.",
    );
  }

  return createHash("sha256").update(secret, "utf8").digest();
}

function encode(value: Buffer): string {
  return value.toString("base64url");
}

function decode(value: string): Buffer {
  return Buffer.from(value, "base64url");
}

export function encryptSession(session: BffSession): string {
  const iv = randomBytes(12);

  const cipher = createCipheriv(
    "aes-256-gcm",
    getKey(),
    iv,
  );

  cipher.setAAD(Buffer.from(VERSION, "utf8"));

  const plaintext = Buffer.from(
    JSON.stringify(session),
    "utf8",
  );

  const ciphertext = Buffer.concat([
    cipher.update(plaintext),
    cipher.final(),
  ]);

  const tag = cipher.getAuthTag();

  return [
    VERSION,
    encode(iv),
    encode(tag),
    encode(ciphertext),
  ].join(".");
}

export function decryptSession(
  value: string | undefined,
): BffSession | null {
  if (!value) {
    return null;
  }

  try {
    const [
      version,
      ivEncoded,
      tagEncoded,
      ciphertextEncoded,
    ] = value.split(".");

    if (
      version !== VERSION ||
      !ivEncoded ||
      !tagEncoded ||
      !ciphertextEncoded
    ) {
      return null;
    }

    const decipher = createDecipheriv(
      "aes-256-gcm",
      getKey(),
      decode(ivEncoded),
    );

    decipher.setAAD(
      Buffer.from(VERSION, "utf8"),
    );

    decipher.setAuthTag(
      decode(tagEncoded),
    );

    const plaintext = Buffer.concat([
      decipher.update(
        decode(ciphertextEncoded),
      ),
      decipher.final(),
    ]);

    const parsed = JSON.parse(
      plaintext.toString("utf8"),
    ) as Partial<BffSession>;

    if (
      typeof parsed.accessToken !== "string" ||
      !parsed.accessToken ||
      typeof parsed.refreshToken !== "string" ||
      !parsed.refreshToken
    ) {
      return null;
    }

    return {
      accessToken: parsed.accessToken,
      refreshToken: parsed.refreshToken,
    };
  } catch {
    return null;
  }
}

export function getBffSessionCookieName(): string {
  return COOKIE_NAME;
}