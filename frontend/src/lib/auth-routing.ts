export function authLandingPath(
  mfaEnrollmentRequired: boolean,
  mfaChallengeRequired: boolean,
  hasWorkspace: boolean,
): string {
  if (mfaEnrollmentRequired) return "/mfa?mode=enroll";
  if (mfaChallengeRequired) return "/mfa?step_up=1";
  return hasWorkspace ? "/dashboard" : "/onboarding";
}
