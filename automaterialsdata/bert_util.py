import torch
import pandas as pd
import numpy as np

def embed_text(text, model, tokenizer):    
    """
       function for embedding a piece of text
    """
    input_ids = torch.tensor(tokenizer.encode(text)).unsqueeze(0)  # Batch size 1
    outputs = model(input_ids)
    
    # The last hidden-state is the first element of the output tuple
    last_hidden_states = outputs[0]  
    
    return last_hidden_states 

def get_similarity(em, em2):    
    """
       function using cosine similarity on 2 embeddings
    """
    return cosine_similarity(em.detach().numpy(), em2.detach().numpy())

def make_embeddings_from_csv(file_path, number_files, start_index, model, tokenizer):
    """
       make embeddings, one batch
    """
    abstract_list = []
    embedding_list = [] 

    data = pd.read_csv(file_path, encoding = "ISO-8859-1")
    i = 1
    end_index = start_index + number_files

    for abstract in data.iloc[start_index:end_index, 1]:
        if i <= number_files:
            print('Embedding paper %i' % (start_index + i))
            embedding_list.append(embed_text(abstract, model, tokenizer).mean(1))
            abstract_list.append(abstract)
            print('  Done!')
        i+=1

    return torch.cat(embedding_list, dim = 0), abstract_list, data.iloc[start_index:end_index,2], data.iloc[start_index:end_index,3]

def make_embeddings(file_path, n_papers, embed_dim, n_paper_per_batch, model, tokenizer):
    """
       make embeddings with batches
    """
    i_batch = 0
    
    finalappend = []
    
    for i in range(0, n_papers, n_paper_per_batch): 
        n_to_do = min(n_papers - i,  n_paper_per_batch)
        embed_list, abstract_list, doi_list, source_list = make_embeddings_from_csv(file_path, n_to_do, i, model, tokenizer)

        for (embed, abstract, doi, source) in zip(embed_list, abstract_list, doi_list, source_list):
            toappend = []
            toappend = embed.detach().numpy().tolist()
            toappend.append(abstract)
            toappend.append(doi)
            toappend.append(source)
            finalappend.append(toappend)
            
    return pd.DataFrame(data=finalappend)
