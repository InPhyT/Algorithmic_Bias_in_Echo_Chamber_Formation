#############################
######## ENVIRONMENT ########
#############################

using Pkg                      # Import package manager
Pkg.activate("./Code/Julia")   # Activate Julia environment
Pkg.instantiate()              # Instantiate the Julia environment

#############################
######### PACKAGES ##########
#############################

using Agents                         # ABM framework 
using Random                         # RNG for reproducibility 
using InteractiveDynamics, GLMakie   # Data visualization 
using Statistics: mean               # Statistical functions  

#############################
###### SHELLING MODEL #######
#############################

"""
To set up an ABM simulation in Agents.jl, a user only needs to follow these steps:

1. Choose in what kind of space the agents will live in, for example a graph, a grid, etc. Several spaces are provided by Agents.jl and can be initialized immediately.
2. Define the agent type (or types, for mixed models) that will populate the ABM. This is defined as a standard Julia mutable struct that is a subtype of AbstractAgent. The type must contain two mandatory fields id, pos, with the position field being appropriate for the chosen space. The remaining fields of the agent type are up to user's choice.
3. The created agent type, the chosen space, and optional additional model level properties (typically in the form of a dictionary) are given to our universal structure AgentBasedModel. This instance defines the model within an Agents.jl simulation. Further options are also available, regarding schedulers and random number generation.
4. Provide functions that govern the time evolution of the ABM. A user can provide an agent-stepping function, that acts on each agent one by one, and/or model-stepping function, that steps the entire model as a whole. These functions are standard Julia functions that take advantage of the Agents.jl API. Once these functions are created, they are simply passed to step! to evolve the model.
5. [Optional] Visualize the model and animate its time evolution. This can help checking that the model behaves as expected and there aren't any mistakes, or can be used in making figures for a paper/presentation.
6. Collect data. To do this, specify which data should be collected, by providing one standard Julia Vector of data-to-collect for agents, for example [:mood, :wealth], and another one for the model. The agent data names are given as the keyword adata and the model as keyword mdata to the function run!. This function outputs collected data in the form of a DataFrame.
"""

# Create the ambient space
space = GridSpace((10, 10); periodic=false)

# Define the agent type
mutable struct SchellingAgent <: AbstractAgent
    id::Int             # The identifier number of the agent
    pos::NTuple{2, Int} # The x, y location of the agent on a 2D grid
    mood::Bool          # whether the agent is happy in its position. (true = happy)
    group::Int          # The group of the agent, determines mood as it interacts with neighbors
end

"""
Notice also that we could have taken advantage of the macro @agent as follows: 
@agent SchellingAgent GridAgent{2} begin
    mood::Bool
    group::Int
end
"""

# Specify the agent-based model 
properties = Dict(:min_to_be_happy => 3)
scheduler  = Schedulers.by_property(:group)
schelling  = ABM(SchellingAgent, space; properties)

function initialize(; N = 320, M = 20, min_to_be_happy = 3, seed = 125)
    space = GridSpace((M, M), periodic = false)
    properties = Dict(:min_to_be_happy => min_to_be_happy)
    rng = Random.MersenneTwister(seed)
    model = ABM(
        SchellingAgent, space;
        properties, rng, scheduler = Schedulers.randomly
    )

    for n in 1:N
        agent = SchellingAgent(n, (1, 1), false, n < N / 2 ? 1 : 2)
        add_agent_single!(agent, model)
    end
    return model
end

# Define the agent-level micro-dynamics  
function agent_step!(agent, model)
    minhappy = model.min_to_be_happy
    count_neighbors_same_group = 0
    for neighbor in nearby_agents(agent, model)
        if agent.group == neighbor.group
            count_neighbors_same_group += 1
        end
    end
    if count_neighbors_same_group ≥ minhappy
        agent.mood = true
    else
        move_agent_single!(agent, model)
    end
    return
end

# Initialize the agent-based model 
model = initialize()
#step!(model, agent_step!)
#step!(model, agent_step!, 3)

# Data visualization
groupcolor(a) = a.group == 1 ? :blue : :orange
groupmarker(a) = a.group == 1 ? :circle : :rect
fig, _ = abmplot(model; ac = groupcolor, am = groupmarker, as = 10)
display(fig)

# Data collection 
adata = [:mood, :group]
model = initialize()
data, _ = run!(model, agent_step!, 5; adata)

x(agent) = agent.pos[1]
model = initialize()
adata = [x, :mood]
data, _ = run!(model, agent_step!, 5; adata)

model = initialize();
adata = [(:mood, sum), (x, mean)]
data, _ = run!(model, agent_step!, 5; adata)

#############################
######## REFERENCES #########
#############################

"""
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
""""