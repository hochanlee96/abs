import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

export default NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: { params: { scope: "openid email profile" } }
    })
  ],
  callbacks: {
    async jwt({ token, account }) {
      // Google provider가 id_token을 내려주는 경우가 많음
      if (account?.id_token) (token as any).id_token = account.id_token;
      return token;
    },
    async session({ session, token }) {
      (session as any).id_token = (token as any).id_token;
      return session;
    }
  }
});
