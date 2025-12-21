import Image from "next/image";
import Link from "next/link";
import { headers } from "next/headers";

// Types
interface Service {
  id: string;
  name: string;
  description: string;
  url: string;
  icon: string;
}

async function getServices(): Promise<Service[]> {
  // In a real scenario, this fetches from the backend API
  // We use the docker service name since this is server-side
  try {
    const res = await fetch("http://lymphhub-backend:8000/api/services", {
      cache: "no-store",
    });
    if (!res.ok) throw new Error("Failed to fetch services");
    return res.json();
  } catch (e) {
    // Fallback if backend is not reachable during build/dev
    console.error(e);
    return [
      { id: "plane", name: "Plane", url: "https://todo.lyckabc.xyz", description: "Project Management", icon: "✈️" },
      { id: "keycloak", name: "Keycloak", url: "https://auth.lyckabc.xyz", description: "Identity Provider", icon: "🔐" },
      { id: "pgadmin", name: "pgAdmin", url: "#", description: "Database Management", icon: "🐘" },
    ];
  }
}

async function getUser() {
  const headersList = await headers();
  const user = headersList.get("x-auth-request-user");
  const email = headersList.get("x-auth-request-email");
  return { user, email };
}

export default async function Home() {
  const services = await getServices();
  const { user, email } = await getUser();
  // If not authenticated (local dev), show guest
  const displayName = user || "Guest";

  return (
    <main className="min-h-screen p-8 md:p-24 flex flex-col items-center relative overflow-hidden">

      {/* Background Orbs */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
      <div className="absolute top-0 right-0 w-96 h-96 bg-yellow-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
      <div className="absolute -bottom-8 left-20 w-96 h-96 bg-pink-500 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-4000"></div>

      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm lg:flex mb-12">
        <p className="fixed left-0 top-0 flex w-full justify-center border-b border-gray-300 bg-gradient-to-b from-zinc-200 pb-6 pt-8 backdrop-blur-2xl dark:border-neutral-800 dark:bg-zinc-800/30 dark:from-inherit lg:static lg:w-auto lg:rounded-xl lg:border lg:bg-gray-200 lg:p-4 lg:dark:bg-zinc-800/30">
          Welcome back,&nbsp;
          <code className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600">
            {email || displayName}
          </code>
        </p>
        <div className="fixed bottom-0 left-0 flex h-48 w-full items-end justify-center bg-gradient-to-t from-white via-white dark:from-black dark:via-black lg:static lg:h-auto lg:w-auto lg:bg-none">
          <span className="text-xs text-gray-400">Powered by Keycloak & Traefik</span>
        </div>
      </div>

      <div className="relative z-10 flex flex-col items-center justify-center mb-16">
        <h1 className="text-6xl font-extrabold tracking-tight mb-4 text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-blue-500 to-purple-600 text-glow">
          LymphHub
        </h1>
        <p className="text-lg text-slate-400 max-w-2xl text-center">
          Centralized command center for your internal services. Secure, unified, and simplified.
        </p>
      </div>

      <div className="relative z-10 grid text-center lg:max-w-5xl lg:w-full lg:mb-0 lg:grid-cols-3 lg:text-left gap-6">

        {services.map((service) => (
          <Link
            key={service.id}
            href={service.url}
            className="group rounded-2xl border border-white/5 bg-white/5 px-5 py-6 transition-all hover:bg-white/10 hover:shadow-2xl hover:scale-105 hover:border-purple-500/50"
            rel="noopener noreferrer"
          >
            <div className="flex items-center gap-4 mb-4">
              <span className="text-4xl bg-white/10 p-3 rounded-xl group-hover:bg-purple-500/20 transition-colors">
                {service.icon}
              </span>
              <h2 className={`text-2xl font-semibold`}>
                {service.name}{" "}
                <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
                  -&gt;
                </span>
              </h2>
            </div>
            <p className={`m-0 max-w-[30ch] text-sm opacity-50 group-hover:opacity-100 transition-opacity`}>
              {service.description}
            </p>
            <div className="mt-4 flex items-center gap-2 text-xs text-green-400">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              Operational
            </div>
          </Link>
        ))}

      </div>
    </main>
  );
}
