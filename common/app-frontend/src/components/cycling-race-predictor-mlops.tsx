"use client"

import React, { useState, useEffect } from 'react'
import Image from 'next/image'
import { ChevronDown, RefreshCw } from 'lucide-react'
import axios from 'axios'

interface Race {
  id: number
  name: string
  stage: string
  index: number
}

interface Cyclist {
  id: number
  name: string
  winPercentage: string
  imageUrl: string
}

export default function CyclingRacePredictor() {
  const predefinedRaces: Race[] = [
    { id: 0, name: 'Reset', stage: 'One Day', index: 0 },
    { id: 1, name: 'Tour Down Under', stage: 'Stage 6', index: 5 },
    { id: 2, name: 'Great Ocean Race', stage: 'One Day', index: 6 },
    { id: 3, name: 'UAE Tour', stage: 'Stage 7', index: 13 },
    { id: 4, name: 'Omloop Het Nieuwsblad', stage: 'One Day', index: 14 },
    { id: 5, name: 'Strade Bianche', stage: 'One Day', index: 15 },
    { id: 6, name: 'Paris-Nice', stage: 'Stage 8', index: 23 },
    { id: 7, name: 'Tirreno-Adriatico', stage: 'Stage 6', index: 28 },
    { id: 8, name: 'Milano-Sanremo', stage: 'One Day', index: 29 },
    { id: 9, name: 'Volta a Catalunya', stage: 'Stage 7', index: 36 },
    { id: 10, name: 'Classic Brugge-De Panne', stage: 'One Day', index: 37 },
    { id: 11, name: 'E3 Harelbeke', stage: 'One Day', index: 38 },
    { id: 12, name: 'Gent-Wevelgem', stage: 'One Day', index: 39 },
    { id: 13, name: 'Dwars door Vlaanderen', stage: 'One Day', index: 40 },
    { id: 14, name: 'Itzulia Basque Country', stage: 'Stage 6', index: 46 },
    { id: 15, name: 'Amstel Gold Race', stage: 'One Day', index: 47 },
    { id: 16, name: 'La Flèche Wallonne', stage: 'One Day', index: 48 },
    { id: 17, name: 'Liège-Bastogne-Liège', stage: 'One Day', index: 49 },
    { id: 18, name: 'Tour de Romandie', stage: 'Stage 5', index: 55 },
    { id: 19, name: 'Eschborn-Frankfurt', stage: 'One Day', index: 56 },
    { id: 20, name: 'Giro d’Italia', stage: 'Stage 21', index: 76 },
    { id: 21, name: 'Critérium du Dauphiné', stage: 'Stage 8', index: 84 },
    { id: 22, name: 'Tour de Suisse', stage: 'Stage 8', index: 92 },
    { id: 23, name: 'Tour de France', stage: 'Stage 21', index: 110 },
    { id: 24, name: 'San Sebastián', stage: 'One Day', index: 111 },
    { id: 25, name: 'Tour de Pologne', stage: 'Stage 7', index: 118 },
    { id: 26, name: 'Vuelta a España', stage: 'Stage 21', index: 138 },
    { id: 27, name: 'Bretagne Classic', stage: 'One Day', index: 139 },
    { id: 28, name: 'Renewi Tour', stage: 'Stage 5', index: 142 },
    { id: 29, name: 'Cyclassics Hamburg', stage: 'One Day', index: 143 },
    { id: 30, name: 'Grand Prix Québec', stage: 'One Day', index: 144 },
    { id: 31, name: 'Grand Prix Montréal', stage: 'One Day', index: 145 },
    { id: 32, name: 'Il Lombardia', stage: 'One Day', index: 146 },
    { id: 33, name: 'Tour of Guangxi', stage: 'Stage 6', index: 152 },
];

  const [racesRedeployment] = useState<Race[]>(predefinedRaces);
  const [races, setRaces] = useState<Race[]>([])
  const [selectedRace, setSelectedRace] = useState<Race | undefined>()
  const [selectedStage, setSelectedStage] = useState<string>('Stage 1')
  const [stages, setStages] = useState<string[]>([])
  const [topCyclists, setTopCyclists] = useState<Cyclist[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [redeploying, setRedeploying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)
  const [deploymentIndex, setDeploymentIndex] = useState<number | ''>('')

  useEffect(() => {
    fetchRaces()
  }, [])

  const fetchRaces = async () => {
    try {
      const response = await axios.get('http://seito.lavbic.net:5010/races')
      if (response.data.length > 0 && deploymentIndex === '') {
        setRaces(response.data)
        setDeploymentIndex(response.data[0].index)
      }
    } catch (err) {
      setError('Failed to load races. Please try again.')
      console.error(err)
    }
  }

  const handleRedeploy = async () => {
    if (deploymentIndex === '') {
      setError('Please select a deployment index')
      return
    }
    
    setRedeploying(true)
    setError(null)
    
    try {
      await axios.post('http://seito.lavbic.net:5010/redeploy', {
        index: deploymentIndex
      })
      
      // Refresh the races list first
      await fetchRaces()
      
      // Then reload the page
      window.location.reload()
    } catch (err) {
      console.error('Redeployment failed:', err)
      setError('Redeployment failed. Please try again.')
    } finally {
      setRedeploying(false)
    }
  }

  const handleRaceChange = async (race: Race) => {
    setSelectedRace(race)
    setIsOpen(false)

    if (!race) {
      console.error('No race selected')
      return
    }

    try {
      if (race.stage === 'One_Day') {
        setStages([])
        await fetchPredictions(race.index)
      } else if (race.stage.startsWith('Stage')) {
        const raceStages = races.filter(r => r.name === race.name)
        
        const totalStages = Math.max(...raceStages.map(r => {
          const match = r.stage.match(/Stage (\d+)/)
          return match ? parseInt(match[1], 10) : 0
        }))

        const newStages = Array.from({ length: totalStages }, (_, i) => `Stage ${i + 1}`)
        setStages(newStages)
        setSelectedStage('Stage 1')

        const stage1Race = raceStages.find(r => r.stage === 'Stage 1')
        if (stage1Race) {
          await fetchPredictions(stage1Race.index)
        } else {
          console.error('Could not find Stage 1 for race:', race.name)
        }
      }
    } catch (error) {
      console.error('Error in handleRaceChange:', error)
      setError('Failed to load race predictions')
    }
  }

  const handleStageChange = (stage: string) => {
    setSelectedStage(stage)
    
    const raceStage = races.find(r => r.name === selectedRace?.name && r.stage === stage)
    if (raceStage) {
      fetchPredictions(raceStage.index)
    }
  }

  const fetchPredictions = async (raceIndex: number) => {
    setLoading(true)
    setError(null)
    
    try {
      const response = await axios.post('http://seito.lavbic.net:5010/predict', { index: raceIndex })
      
      const predictionData = response.data.prediction

      const cyclists = predictionData.map((cyclist: { name: string, image_url: string, prediction: number }, i: number) => ({
        id: i + 1,
        name: cyclist.name,
        winPercentage: (cyclist.prediction * 100).toFixed(2),
        imageUrl: cyclist.image_url
      }))

      setTopCyclists(cyclists)
    } catch (err) {
      console.error('Error fetching predictions:', err)
      setError('Failed to fetch predictions. Please try again.')
      setTopCyclists([])
    } finally {
      setLoading(false)
    }
  }

  const displayedCyclists = showAll ? topCyclists : topCyclists.slice(0, 10)

  return (
    <div className="min-h-screen bg-cover bg-center p-4">
      <div className="max-w-4xl mx-auto bg-white/95 backdrop-blur-sm rounded-lg shadow-lg">
        <div className="p-6">
          <div className="flex flex-col space-y-4 mb-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold">Cycling Race Predictor</h2>
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2">
                  <label htmlFor="deploymentIndex" className="text-sm font-medium text-gray-700">
                    Race to redeploy:
                  </label>
                  <select
                    id="deploymentIndex"
                    value={deploymentIndex}
                    onChange={(e) => setDeploymentIndex(e.target.value ? Number(e.target.value) : '')}
                    className="p-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
                  >
                    <option value="">Select race</option>
                    {racesRedeployment.map((race) => (
                      <option key={race.index} value={race.index}>
                        {race.id} - {race.name}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  onClick={handleRedeploy}
                  disabled={redeploying || deploymentIndex === ''}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-md text-white 
                    ${(redeploying || deploymentIndex === '') ? 'bg-gray-400' : 'bg-primary hover:bg-primary/90'}`}
                >
                  <RefreshCw className={`h-5 w-5 ${redeploying ? 'animate-spin' : ''}`} />
                  <span>{redeploying ? 'Redeploying...' : 'Redeploy Model'}</span>
                </button>
              </div>
            </div>
            {error && <p className="text-center text-red-500">{error}</p>}
          </div>
          
          <div className="relative mb-6">
            <button
              onClick={() => setIsOpen(!isOpen)}
              className="w-full p-2 bg-white border border-gray-300 rounded-md shadow-sm text-left flex justify-between items-center focus:outline-none focus:ring-2 focus:ring-primary"
              aria-haspopup="listbox"
              aria-expanded={isOpen}
            >
              <span className="block truncate">
                {selectedRace ? selectedRace.name : 'Select a race'}
              </span>
              <ChevronDown className={`h-5 w-5 text-gray-400 transform ${isOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
            </button>

            {isOpen && (
              <ul
                className="absolute z-10 mt-2 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm"
                role="listbox"
              >
                {Array.from(new Set(races.map((race) => race.name))).map((name) => {
                  const race = races.find((r) => r.name === name)
                  if (!race) return null
                  
                  return (
                    <li
                      key={name}
                      className={`cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-primary hover:text-white ${
                        name === selectedRace?.name ? 'bg-primary text-white' : 'text-gray-900'
                      }`}
                      onClick={() => handleRaceChange(race)}
                      role="option"
                    >
                      {name}
                    </li>
                  )
                })}
              </ul>
            )}
          </div>

          {stages.length > 0 && (
            <div className="relative mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-1">Select Stage</label>
              <select
                value={selectedStage}
                onChange={(e) => handleStageChange(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary"
              >
                {stages.map((stage, index) => (
                  <option key={index} value={stage}>{stage}</option>
                ))}
              </select>
            </div>
          )}

          {loading && <p className="text-center">Loading predictions...</p>}
          {error && <p className="text-center text-red-500">{error}</p>}

          {selectedRace && topCyclists.length > 0 && !loading && (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Cyclists</h3>
                <button
                  onClick={() => setShowAll(!showAll)}
                  className="p-1 px-4 bg-primary text-white rounded-md"
                >
                  {showAll ? 'Show Top 10' : 'Show All'}
                </button>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="p-2 text-left">Rank</th>
                    <th className="p-2 text-left">Cyclist</th>
                    <th className="p-2 text-left">Win Likelihood</th>
                  </tr>
                </thead>
                <tbody>
                  {displayedCyclists.map((cyclist, index) => (
                    <tr key={cyclist.id} className="border-b">
                      <td className="p-2">{index + 1}</td>
                      <td className="p-2">
                        <div className="flex items-center space-x-2">
                          <Image
                            src={cyclist.imageUrl}
                            alt={`${cyclist.name}'s avatar`}
                            width={40}
                            height={40}
                            className="rounded-full"
                          />
                          <span>{cyclist.name}</span>
                        </div>
                      </td>
                      <td className="p-2">{cyclist.winPercentage}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}