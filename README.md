</p>
<!-- Title -->
<h1 align="center">
  Computational Social Science Project
</h1>

<h2 align="center">
  Algorithmic Bias in Echo Chamber Formation
</h2>
<!-- Badges -->
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/InPhyT/Algorithmic_Bias_in_Echo_Chamber_Formation/blob/main/LICENSE)

## Goal
The research question is to assess algorithmic impact on Twitter echo chamber formation. In order to minimize biases, we observe the same user pool debating over the same topic (US Elections) before and after the introduction of the recommendation algorithm in 2014. Therefore, exploiting a complete dataset of 2012 tweets relative to 2012 U.S. elections, we extract a sample of users  to initialize, calibrate and validate an ABM to describe an free Twitter. The follow, retweet, favorite, mention (including replies) and hashtag  emission of the same pool of users is being monitored in order to get the data needed to later model today's algorithm-biased Twitter echo chamber dynamics and compare it with what would predict the validated algorithm-free model. So we organized the work so far as follows. 

## Definitions

### Recommendation algorithm 
A **recommendation algorithm** is a algorithm whose inputs are all the tweets produced at a certain model iteration and outputs the feed for each user during next iteration.

### Parametric algorithm 
The **parametric algorithm** is a recommendation algorithm explicitly implemented by us, that takes into account (via parameters to be set/fitted) the agents' full activity. It is said to be **free** if it produces each user's feed only looking at who her friends are and in what chronological order they tweeted. Twitter is called *free* if endowed with a free parametric recommendation algorithm.

### Echo chamber 
An **echo chamber** on a graph is a subgraph defined by two conditions:

1. It is recognized as a cluster by a (given) clustering algorithm
2. It must exceed a certain *opinion homogeneity threshold*, given a measure of opinion homogeneity on a subgraph. 

## Data 
### 2012 collection
#### Tweets selection & initial processing
We collected all 2012 tweet objects filtering out all the irrelevant fields and selecting only english tweets. 

#### Users selection
We performed a two-step selection over the remaining pool of tweets:

- hashtag-based user mining
- subscription date based user selection (i.e we kept only those still-existing users whose subscription date is the same as the one we got from 2012 data).

### 2020 collection
#### Multithread interaction network scraping

We scraped, their timeline-aggregated interaction (retweet, mention) network and identified all the users who took part in it (i.e. they are connected to at least one other user). 

This way we obtained a pool of $\sim 10,000$ users that both took part in the 2012 U.S. election debate and still exist today, allowing us to compare echo chambers formation before and after the introduction of the recommendation algorithm.

#### Multithread monitoring strategy deployment
A detailed temporal activity monitoring pipeline has been launched over such $10,000$ users. This will allow us to associate a timestamp to events (such as follow activity) which would otherwise have no time indication or ordering should one use Twitter historical API. We need to gather temporal information of such  detailed activity in order to later model Twitter dynamics and then reproduce it with a parametric algorithm. 

## Agent-Based Model

### Computational Framework

The framework we used is [Agents.jl](https://juliadynamics.github.io/Agents.jl/stable/), an intuitive yet powerful ABM Julia library . A key ingredient in Agents.jl ABM models is the *base space*, for which we adopted an ad-hoc extension of [Graphs.jl](https://juliagraphs.org/Graphs.jl/stable/) model.

### Overview

The ambient space of the model consists in a 4-layer multiplex graph, whose levels are the follow, retweet, favorite and mention (including replies) networks. 

Each node is occupied by an agent that represents a Twitter user. 
Agents are initialized with activity rate parameters drawn from the data, including its opinion about the Democrat/Republican debate encoded in a real number $o \in [-1,+1]$.

The tweet is an object composed of the author id and her opinion at the time of writing.

At each iteration of the model dynamics, each agent reads the tweets selected and ordered for her by the recommendation algorithm (albeit topological), consequently changes her opinion via an opinion dynamics model and decides who to follow, unfollow, retweet, unretweet, etc.  

#### Initialization, calibration & validation

A time step is selected so that it encompasses a statistically significant portion of 2012 data. The distributions extracted from the first temporal slice is used to initialize the model. The rest, except for the last slice, is instead adopted to calibrate the model (parameters such as changes in activity rates).<br>
The last slice will be used for validation. 

### Recommendation Algorithm 
#### 2020 Twitter dynamics
From the data scraped using the monitor, we intend to train and validate a model able to perform link prediction on the multiplex graph of our ABM. Later, we aim to fit the parametric algorithm on the dynamics predicted by the link prediction model on the multiplex graph. Such fitted parametric algorithm will output the predicted feeds of all users. This in turn will let us draw a temporal directed **tweet network**, whose nodes are users and edges from user $i$ to user $j$ iff user $j$ read a tweet of $i$. This new network encodes the actual information flow on Twitter, the one where the concept of echo chambers makes sense.