"use client"

import React, { useState, useEffect } from 'react'
import Image from 'next/image'
import { ChevronDown } from 'lucide-react'
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
  const [races, setRaces] = useState<Race[]>([])
  const [selectedRace, setSelectedRace] = useState<Race | undefined>()
  const [selectedStage, setSelectedStage] = useState<string>('Stage 1')
  const [stages, setStages] = useState<string[]>([])
  const [topCyclists, setTopCyclists] = useState<Cyclist[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    axios.get('http://seito.lavbic.net:5010/races')
      .then((response) => {
        setRaces(response.data)
      })
      .catch((err) => {
        setError('Failed to load races. Please try again.')
        console.error(err)
      })
  }, [])

  const handleRaceChange = async (race: Race) => {
    setSelectedRace(race)
    setIsOpen(false)

    if (!race) {
      console.error('No race selected')
      return
    }

    try {
      if (race.stage === 'One_Day') {
        // Handle one-day races
        setStages([])
        await fetchPredictions(race.index)
      } else if (race.stage.startsWith('Stage')) {
        // Handle stage races
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
          <h2 className="text-2xl font-bold text-center mb-6">Cycling Race Predictor</h2>
          
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