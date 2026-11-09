export function countUniqueInviteSeats(
  ownerEmail: string,
  inviteEmails: string[],
  approverEmail: string,
): number {
  const uniqueEmails = new Set(
    [ownerEmail, ...inviteEmails, approverEmail]
      .map((email) => email.trim().toLowerCase())
      .filter(Boolean),
  );
  return Math.max(1, uniqueEmails.size);
}
