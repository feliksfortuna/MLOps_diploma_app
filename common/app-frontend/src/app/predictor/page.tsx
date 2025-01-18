"use client"

import dynamic from 'next/dynamic';
import React from 'react';

const PredictorPage = () => {
  // Determine the deployment type at runtime
  const isMLOps = process.env.NEXT_PUBLIC_DEPLOYMENT_TYPE === 'mlops';

  // Dynamically import the appropriate component
  const Component = dynamic(
    () =>
      isMLOps
        ? import('@/components/cycling-race-predictor-mlops')
        : import('@/components/cycling-race-predictor-devops'),
    { ssr: false }
  );

  return <Component />;
};

export default PredictorPage;