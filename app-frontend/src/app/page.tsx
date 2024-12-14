import Link from 'next/link'

export default function WelcomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-primary to-secondary flex flex-col items-center justify-center p-4 text-white">
      <h1 className="text-4xl font-bold mb-4 text-center">Welcome to Cycling Race Predictor</h1>
      <p className="text-xl mb-8 text-center max-w-2xl">
        Discover the top cyclists and their winning chances in major races around the world.
      </p>
      <Link 
        href="/predictor" 
        className="bg-white text-primary hover:bg-opacity-90 transition-all duration-300 font-bold py-3 px-6 rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-1 active:translate-y-0"
      >
        Go to Race Predictor
      </Link>
    </div>
  )
}