import { createAuthClient } from "better-auth/react";

export const authClient = createAuthClient({
  baseURL: "https://ep-bold-glitter-b324brx0.neonauth.c-4.ap-southeast-1.aws.neon.tech/neondb/auth"
});

export const { signIn, signUp, signOut, useSession } = authClient;
