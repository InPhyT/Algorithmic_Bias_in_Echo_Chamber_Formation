# MULTIPLEX GRAPHS JULIA PACKAGE 
# LAST UPDATE: 04-10-2020

module MultiplexGraphs

###################################
######## REQUIRED PACKAGES ########
###################################
using LightGraphs, SimpleWeightedGraphs, Base, Agents, SparseArrays

import LightGraphs: nv, ne, has_edge, has_vertex, add_edge!, rem_edge!, rem_vertex!,
    rem_vertices!, add_vertex!, add_vertices!, outneighbors, inneighbors, vertices, edges,
    adjacency_matrix, src, dst, nv, edgetype
import SimpleWeightedGraphs
import Base: show, eltype, copy
import Agents: node_neighbors


# Define the MultiplexGraph mutable struct
mutable struct MultiplexGraph{T <: Int} <: AbstractGraph{T} #{T <: Integer}
    #n::Int64
    #src = Vector{T}
    follower_graph::SimpleWeightedDiGraph
    retweet_graph::SimpleWeightedDiGraph
    favorite_graph::SimpleWeightedDiGraph
    # Temporary constructor
    function MultiplexGraph(n::Int) # to be added the src/dst/weights constructor
        follower_graph = SimpleWeightedDiGraph{Int,Int}(n)
        retweet_graph = SimpleWeightedDiGraph{Int,Int}(n)
        favorite_graph = SimpleWeightedDiGraph{Int,Int}(n)
        return new{Int}(follower_graph,retweet_graph,favorite_graph) 
    end
end

# Check the existence of a given edge
function has_edge(mp::MultiplexGraph, s::Int, d::Int, which::Symbol)
    return SimpleWeightedGraphs.has_edge(getfield(mp, which) , s , d )
end

# Extract the weight of a given edge
function get_weight(mp::MultiplexGraph, s::Int, d::Int, which::Symbol)
    return SimpleWeightedGraphs.weights(getfield(mp, which))[s,d]
end

# Add an edge 
function add_edge!(mp::MultiplexGraph, s::Int, d::Int, which::Symbol , weight::Int = 1 )
    current_weight = get_weight(mp,s,d,which)
    if which == :follower_graph && !(weight in [1,-1])
        return error("Error: follower graph weights must be 1.")
    elseif which == :follower_graph && current_weight == 1 && weight == 1
        return error("Error: edge already esisting.")
    else
        if current_weight+weight != 0
            SimpleWeightedGraphs.add_edge!(getfield(mp,which) ,s,d ,current_weight+weight)
        else  
            SimpleWeightedGraphs.rem_edge!(getfield(mp,which) ,s,d)
        end
    end
end

# Extract an array of all edges 
function edges(mp::MultiplexGraph, which::Symbol)
    return [edge for edge in SimpleWeightedGraphs.edges(getfield(mp,which)) if edge.weight != 0  ]
end
# PLEASE CONSIDER IMPLEMENTING nodes((mp::MultiplexGraph, which::Symbol) !

# Check graph type
eltype(mp::MultiplexGraph{T}) where {T <: Int} = T
# Check the edge type
edgetype(mp::MultiplexGraph{T}) where {T <: Int} = SimpleWeightedGraphs.edgetype(mp.retweet_graph)

# Extract the array of in-neighbors of a given vertex
function neighbors(mp::MultiplexGraph{T}, v::T, which::Symbol) where {T <: Int}
    return collect(SimpleWeightedGraphs.neighbors(getfield(mp, which) ,v))
end
# Extract the array of in-neighbors of a given vertex
function inneighbors(mp::MultiplexGraph{T}, v::T, which::Symbol) where {T <: Int}
    return [n for n in collect(SimpleWeightedGraphs.inneighbors(getfield(mp, which) ,v)) if SimpleWeightedGraphs.weights(getfield(mp, which))[n,v] >0]
end
# Extract the array of out-neighbors of a given vertex
function outneighbors(mp::MultiplexGraph{T}, v::T, which::Symbol) where {T <: Int}
    return [n for n in collect(SimpleWeightedGraphs.outneighbors(getfield(mp, which),v)) if SimpleWeightedGraphs.weights(getfield(mp, which))[v,n] >0]
end

# Check the number of edges 
function ne(mp::MultiplexGraph{T}) where {T <: Int} # which::Symbol)
    return SimpleWeightedGraphs.ne(getfield(mp, :follower_graph))+SimpleWeightedGraphs.ne(getfield(mp, :retweet_graph))+SimpleWeightedGraphs.ne(getfield(mp, :favorite_graph))
end

# Check the number of vertices
function nv(mp::MultiplexGraph{T}) where {T <: Int}
    return SimpleWeightedGraphs.nv(getfield(mp, :follower_graph))
end


# Initialize an empty graph
function zero(::MultiplexGraph{T})  where {T <: Int}
    return MultiplexGraph(0)
end

# Check if the graph is directed 
function is_directed(::MultiplexGraph{T}) where {T <: Integer}
    return true
end

# Extract a given edge
function get_edge(mp::MultiplexGraph, s::Int, d::Int, which::Symbol)
    if has_edge(mp, s,d,which)
        return  SimpleWeightedGraphs.SimpleWeightedEdge(s,d, get_weight(mp,s,d,which))
    else
        return error("Error: specified source and destination in ",which," have no edge between them. Use `edges(mp::MultiplexGraph, which::String)` to get the list of all edges in subnetwork `which`")
    end
end

# Remove a given edge 
function rem_edge!(mp::MultiplexGraph, s::Int, d::Int, which::Symbol , weight::Int = 1)
    current_weight = get_weight(mp, s,d,which)
    if has_edge(mp,s,d,which) && current_weight >= weight
        if which == :follower_graph && !(weight in [1,0])
            return error("Error: follower graph weights must be 1 or 0.")
        else
            add_edge!(mp, s, d , which, -weight)
        end
    else
        return error("The required link does not exist, or the its weight is lesser than the weight to be subracted passed as argument.", "link weight = $current_weight , weight to be subtracted = $weight ")
    end
end

# End Module
end 