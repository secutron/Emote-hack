import torchaudio
from moviepy.editor import VideoFileClip
import os
import torch
import librosa
from transformers import Wav2Vec2Processor, Wav2Vec2Model
import soundfile as sf

# Load the processor and model from HuggingFace Transformers
processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base-960h")

# Function to read in audio file and extract features
def extract_features(audio_path):
    # Load the audio file
    audio_input, sample_rate = sf.read(audio_path)


    # Process the raw audio input
    input_values = processor(audio_input, return_tensors="pt", sampling_rate=sample_rate).input_values

    # Retrieve features from Wav2Vec 2.0
    with torch.no_grad():
        hidden_states = model(input_values).last_hidden_state

    return hidden_states.squeeze().numpy()



# Set device for torch
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load the pre-trained Wav2Vec model
bundle = torchaudio.pipelines.WAV2VEC2_BASE
model = bundle.get_model().to(device)
model.eval()


import numpy as np

def get_nearby_frames_features(A, f, m, n):
    """
    Concatenate feature vectors from nearby frames.
    
    Args:
    A (np.ndarray): An array of shape (num_frames, feature_dim) containing the feature vectors.
    f (int): The current frame index.
    m (int): The number of frames before the current frame to include.
    n (int): The number of frames after the current frame to include.
    
    Returns:
    np.ndarray: The concatenated feature vector for frame f.
    """
    # Initialize the feature vector with the current frame's features
    nearby_frames_features = A[f]
    
    # Concatenate features from previous m frames
    for i in range(1, m + 1):
        if f - i < 0:
            # If the index is out of bounds, you could either skip or use some form of padding
            # Here we use zero padding
            prev_features = np.zeros_like(A[f])
        else:
            prev_features = A[f - i]
        nearby_frames_features = np.concatenate((prev_features, nearby_frames_features))
    
    # Concatenate features from next n frames
    for i in range(1, n + 1):
        if f + i >= len(A):
            # If the index is out of bounds, you could either skip or use some form of padding
            # Here we use zero padding
            next_features = np.zeros_like(A[f])
        else:
            next_features = A[f + i]
        nearby_frames_features = np.concatenate((nearby_frames_features, next_features))
    
    return nearby_frames_features


def extract_features_from_mp4(video_path, model_name='facebook/wav2vec2-base-960h'):
    """
    Extract audio features from an MP4 file using Wav2Vec 2.0.

    Args:
    video_path (str): Path to the MP4 video file.
    model_name (str): Model name or path.

    Returns:
    torch.Tensor: Features extracted from the audio.
    """
    # Load pretrained Wav2Vec 2.0 tokenizer and model from Hugging Face Hub
    processor = Wav2Vec2Processor.from_pretrained(model_name)
    model = Wav2Vec2Model.from_pretrained(model_name)

    # Create the audio file path from the video file path
    audio_path = os.path.splitext(video_path)[0] + '.wav'
    
    # Check if the audio file already exists
    if not os.path.exists(audio_path):
        # Extract audio from video
        video_clip = VideoFileClip(video_path)
        video_clip.audio.write_audiofile(audio_path)

    # Load the audio file
    waveform, sample_rate = sf.read(audio_path)

    # Check if we need to resample
    if sample_rate != processor.feature_extractor.sampling_rate:
        waveform = librosa.resample(np.float32(waveform), orig_sr=sample_rate, target_sr=processor.feature_extractor.sampling_rate)
        sample_rate = processor.feature_extractor.sampling_rate
    # # Ensure waveform is a 1D array for a single-channel audio
    # if waveform.ndim > 1:
    #     waveform = waveform.squeeze()
    # Ensure waveform is a 1D array for a single-channel audio
    if waveform.ndim > 1:
        waveform = waveform.mean(axis=1)  # Taking mean across channels for simplicity

    print("waveform.ndim: ", waveform.ndim)
    # # Check and adjust dimensions
    # # Ensure waveform is 2D (shape: [channels, sequence_length]) or 3D (shape: [batch_size, channels, sequence_length])
    # if waveform.ndim == 4:
    #     waveform = waveform.squeeze()  # Removes the additional dimension
    # elif waveform.ndim == 2:
    #     waveform = waveform.unsqueeze(0)  # Adds a batch dimension
        

    # Check the current length of the waveform
    current_length = waveform.shape[0]
    print("current_length: ", current_length)
    # Define the desired length (for example, 16000 if you want 1 second of audio at 16kHz)
    desired_length = 16000

    # Calculate the padding length needed
    padding_length = max(desired_length - current_length, 0)
    print("padding_length: ", padding_length)
    # Pad the waveform if necessary
    if padding_length > 0:
        waveform = np.pad(waveform, (0, padding_length), mode='constant')

    # Process the audio to extract features
    input_values = processor(waveform, sampling_rate=sample_rate, return_tensors="pt").input_values
    input_values = input_values.to('cuda' if torch.cuda.is_available() else 'cpu')


    # Pass the input_values to the model
    with torch.no_grad():
        hidden_states = model(input_values).last_hidden_state
        
    return hidden_states



# Example usage:
video_path = 'M2Ohb0FAaJU_1.mp4'
A = extract_features_from_mp4(video_path)
print(A.shape)



# Print the size of the features from each layer
for i, feature in enumerate(A):
    print(f"Size of features from layer {i}: {feature.size()}")




# Example usage
# A would be your array of feature vectors
# f is the current frame index
# m is the number of frames before f you want to include
# n is the number of frames after f you want to include
# Now let's get the concatenated features for frame 50 with 2 frames before and after
f = 50
m = 2
n = 2

# Ensure A is squeezed to remove the batch dimension if it's size 1
A = A.squeeze(0) if A.size(0) == 1 else A
nearby_frames_features = get_nearby_frames_features(A, f, m, n)
print(nearby_frames_features.shape)  # This should be (feature_dim * (m + n + 1), )
