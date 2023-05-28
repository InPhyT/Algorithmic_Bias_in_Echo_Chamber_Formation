#############################
######## ENVIRONMENT ########
#############################

using Pkg                               # Import package manager
Pkg.activate("./Code/Julia")            # Activate Julia environment
Pkg.instantiate()                       # Instantiate the Julia environment
#Pkg.update()                           # Update the Julia environment

#############################
######### RESOURCES #########
#############################

""" AGENTS.JL
REPOSITORIES 
- https://github.com/JuliaDynamics/Agents.jl
- https://github.com/JuliaGraphs/Graphs.jl

GIST
- Gist of Agents.jl Introductory Tutorial https://gist.github.com/Datseris/e7e15d3559f8dc69d07bba051d904ebf

DOCUMENTATION 
https://juliadynamics.github.io/Agents.jl/stable/

PAPER
https://doi.org/10.1177%2F00375497211068820

VIDEOS
- "Agents.jl: Introductory Tutorial" https://youtu.be/fgwAfAa4kt0
- "Agents.jl and the next chapter in agent based modelling | Tim DuBois | JuliaCon2021" https://youtu.be/Iaco6v6TVXk
"""

""" MODELS
- Baumann et al. (2020) https://doi.org/10.1103/PhysRevLett.124.048301

"""

#############################
######### PACKAGES ##########
#############################

# Import necessary dependencies
using Graphs, SimpleWeightedGraphs, MetaGraphs 
using DataStructures
using LinearAlgebra, SparseArrays
using MultiplexGraphs
using Agents     
using Random

# Create the ambient space
N = 100 
space = GraphSpace(SimpleWeightedDiGraph(N))

# Create the user agent type
@agent User GraphAgent begin
    opinion::Real         # leaning ∈ [-1,1] 
    follow_rate::Real     # probability to follow another user
    unfollow_rate::Real   # probability to unfollow another user
end

N = 100 
space = GraphSpace(SimpleWeightedDiGraph(N))
model = ABM(User, space)


function model_initialization(; num_agents=100, seed=123)
    space = SimpleWeightedDiGraph(num_agents)
    rng   = Random.MersenneTwister(seed)
    model = ABM(User, space; 
                properties, rng, scheduler = Schedulers.Randomly()
            )


end 

# Set the population size
const N=1000
# Set the number ot time steps 
const nsteps=25
# Set the "controversialness" parameter
α = 0.5 
# Set the follow threshold (model-level property) 
follow_threshold=0.2
# Set the unfollow threshold (model-level property) 
unfollow_threshold=0.4

function model_initialization(N::Int, α::Real, follow_threshold::Real, unfollow_threshold::Real)
    # Initialize the model step to 0 
    step       = 0
    # Create the dictionary of model-level / system-level properties
    properties = @dict(N, step, α, follow_threshold, unfollow_threshold) # or @dict(N) where @dict is a "macro" which is equivalent to  Dict(:N => N)
    # Construct an ambient space as a directed weighted graph
    space      = GraphSpace(SimpleWeightedDiGraph(N))
    # Construct the agent-based model
    model      = ABM(User, space; properties)
    
    # Populate the agent-based model
    for id in 1:N
        # Set the agent position 
        pos = id
        # Draw the agent opinion from a uniform distribution 
        opinion=rand(Uniform(-1, 1))          

        follow_rate=abs(round(Int, activity_data[3,id]))+1    # round(Int, rand(Gamma(3, 1))) 
        unfollow_rate=abs(round(Int, activity_data[3,id]))+1  # round(Int, rand(Gamma(3, 1))) 
        tweets=Array{Int,1}()     
        favorites=Array{Int,1}()  
        add_agent!(pos, model, feed, opinion, tweet_rate, retweet_rate, favorite_rate, follow_rate, unfollow_rate, tweets, favorites) # even though opinion is optional
    end
    
    agents=[a for a in allagents(model)]
    # Initialize follower graph (static)
    for agent in agents
        others=[a for a in agents if a !=agent]
        friends=StatsBase.sample(others, round(Int, rand(Gamma(2, 1))); replace=false, ordered=false) # replace=true for favorite graph
        for friend in friends
            MG.add_edge!(model.space.graph, agent.pos, friend.pos, :follower_graph)
        end
    end
    
    return model
end

# Follow dynamics 
function follow!(agent,model)
    agent.follow_rate==0 && return
    friends_pos=node_neighbors(agent, model, :follower_graph, neighbor_type=:out) 
    friends=[f for f in allagents(model) if f.pos in friends_pos]
    others=[a for a in allagents(model) if a !=agent && a ∉ friends]
    possible_friends=[other for other in others if (sign(agent.opinion)==1 && agent.opinion - model.follow_threshold ≤ other.opinion) || (sign(agent.opinion)==-1 && agent.opinion+model.follow_threshold ≥ other.opinion)]
    other_to_follow=StatsBase.sample(possible_friends, min(agent.follow_rate,length(possible_friends)) ; replace=false, ordered=false)
    for other in other_to_follow
        MG.add_edge!(model.space.graph, agent.pos, other.pos, :follower_graph)
    end
end

# Define 
function unfollow!(agent,model)
    agent.unfollow_rate==0 && return
    friends_pos=node_neighbors(agent, model, :follower_graph, neighbor_type=:out) 
    friends=[f for f in allagents(model) if f.pos in friends_pos]
    controversial_friends=[friend for friend in friends if (sign(agent.opinion)==1 && agent.opinion - model.unfollow_threshold > friend.opinion) || (sign(agent.opinion)==-1 && agent.opinion+model.unfollow_threshold < friend.opinion)]
    friends_to_unfollow = StatsBase.sample(controversial_friends, min(agent.unfollow_rate,length(controversial_friends)) ; replace=false, ordered=false)
    for friend in friends_to_unfollow
        if MG.get_weight(model.space.graph, agent.pos, friend.pos, :follower_graph) == 0 
            agent_pos=agent.pos
            friend_pos=friend.pos
            println("$agent_pos , $friend_pos")
        end
        MG.rem_edge!(model.space.graph, agent.pos, friend.pos, :follower_graph)
    end
end

# Agent dynamics
function agent_step!(agent,model)
    Tweet!(agent,model)
    #Like!(agent,model)
    #RT!(agent,model)
    Update!(agent,model)
    Follow!(agent,model)
    Unfollow!(agent,model)
end;