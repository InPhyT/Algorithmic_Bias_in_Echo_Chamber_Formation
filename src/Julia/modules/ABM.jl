module ABM

function get_deg_seq(N ; K, distrib)
    deg_seq = rand( distrib(0,K),N)
    return deg_seq
end

function get_directed_configuration_model(in_deg_seq,out_deg_seq) #https://stackoverflow.com/questions/48212909/how-can-i-write-an-arbitrary-discrete-distribution-in-julia
    graph = SimpleDiGraph(length(out_deg_seq)) 
    verts = vertices(graph)
    probabilities = in_deg_seq/sum(in_deg_seq)
    weights = Weights(probabilities)
    for (v,out_deg) in zip(vertices(graph),out_deg_seq) #1:length(vertices(graph))#zip(vertices(graph),deg_seq)
        i = 0
        while i <= out_deg
            while true
                global D = sample(verts,weights)
                if D != v
                    break
                else
                    continue
                end
            end
            #print(D, " ")
            add_edge!(graph,v,D)
        i += 1
        end
    end
    return graph
end    

function read_think_post!(agent,model)
    #friends_pos =  inneighbors(model.space.graph, agent.id)
    friends_pos = node_neighbors(agent, model,neighbor_type=:out) #returns the nodes (pos) #https://juliadynamics.github.io/Agents.jl/stable/api/#Agents.node_neighbors
    friends_agents = [get_node_agents(pos, model)[1] for pos in friends_pos]

    friends_opinions = [friend.opinion for friend in friends_agents]

    #think
    agent.opinion = mean(append!(friends_opinions,agent.opinion)) #append! is like extend, push! is like append, vcat is like push but not inplace (muting)
end

### Module end
end