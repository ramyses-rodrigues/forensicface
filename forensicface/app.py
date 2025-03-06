# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/00_forensicface.ipynb.

# %% auto 0
__all__ = ['custom_formatwarning', 'ForensicFace']

# %% ../nbs/00_forensicface.ipynb 2
from nbdev.showdoc import *
from fastcore.utils import *
import onnxruntime
import cv2
import numpy as np
import os.path as osp
from glob import glob
from imutils import build_montages
from insightface.app import FaceAnalysis
from insightface.utils import face_align
from tqdm import tqdm
import warnings
from .utils import freeze_env, transform_keypoints, annotate_img_with_kps
import warnings


def custom_formatwarning(message, category, filename, lineno, line=None):
    return f"{category.__name__}: {message}\n"


warnings.formatwarning = custom_formatwarning

# %% ../nbs/00_forensicface.ipynb 3
class ForensicFace:
    """
    Class for processing facial images to extract useful features for forensic analysis.
    """

    IMG_SIZE = (112, 112)

    def __init__(
        self,
        models: list[str] = ["sepaelv2"],
        model: str = None,
        det_size: int = 320,
        use_gpu: bool = True,
        gpu: int = 0,  # which GPU to use
        concat_embeddings: bool = True,
        extended=True,
    ):
        """
        A face comparison tool for forensic analysis and comparison of facial images.

        Args:
        - models (list[str]): The names of the face recognition models to use (default: ["sepaelv2"]).
        - model (str): [deprecated] The name of the face recognition model to use
        - det_size (int): The size of the input images for face detection (default: 320).
        - use_gpu (bool): Whether to use a GPU for inference (default: True).
        - gpu (int): The ID of the GPU to use (default: 0).
        - concat_embeddings (bool): If True, concatenates the embeddings of each model.
        - extended (bool): Whether to use extended modules (detection, landmark_3d_68, genderage) (default: True).
        """

        if model is not None:
            warnings.warn(
                "__init__: The 'model' parameter is deprecated and will be removed in a future release.\n"
                "Please use the 'models' parameter instead: models = ['model_name']",
                DeprecationWarning,
            )
            self.models = [model]
        else:
            self.models = models
        self.rec_inference_sessions = [
            self._load_model(model_name, use_gpu, gpu) for model_name in self.models
        ]

        self.det_size = (det_size, det_size)
        self.det_thresh = det_thresh
        self.extended = extended
        if self.extended:
            allowed_modules = ["detection", "landmark_3d_68", "genderage"]

            self.ort_fiqa = onnxruntime.InferenceSession(
                osp.join(
                    osp.expanduser("~/.insightface/models"),
                    self.models[0],
                    "cr_fiqa",
                    "cr_fiqa_l.onnx",
                ),
                providers=[("CUDAExecutionProvider", {"device_id": gpu})]
                if use_gpu
                else ["CPUExecutionProvider"],
            )
        else:
            allowed_modules = ["detection"]

        self.detectmodel = FaceAnalysis(
            name=self.models[0],
            allowed_modules=allowed_modules,
            providers=[("CUDAExecutionProvider", {"device_id": gpu})]
            if use_gpu
            else ["CPUExecutionProvider"],
        )
        self.detectmodel.prepare(ctx_id=gpu if use_gpu else -1, det_size=self.det_size)

        self.environment = freeze_env()
        self.concat_embeddings = concat_embeddings

    def _load_model(self, model_name, use_gpu, gpu):
        """Loads a single ONNX model."""
        model_path = glob(
            osp.join(
                osp.expanduser("~/.insightface/models"), model_name, "*", "*face*.onnx"
            )
        )
        assert len(model_path) == 1, f"More than one ONNX model found in {model_path}"
        return onnxruntime.InferenceSession(
            model_path[0],
            providers=(
                [("CUDAExecutionProvider", {"device_id": gpu})]
                if use_gpu
                else ["CPUExecutionProvider"]
            ),
        )

    def _to_input_ada(self, aligned_bgr_img):
        """
        Preprocesses the input face for the face recognition model.

        Args:
            face: Face image as a numpy array in BGR order.

        Returns:
            Preprocessed face image as a numpy array.
        """
        _aligned_bgr_img = aligned_bgr_img.astype(np.float32)
        _aligned_bgr_img = ((_aligned_bgr_img / 255.0) - 0.5) / 0.5
        return _aligned_bgr_img.transpose(2, 0, 1).reshape(1, 3, *self.IMG_SIZE)

    def _get_best_face(self, img, faces, criterion="size"):
        """Get the best face based on a criterion: 'centrality' or 'size'."""
        assert criterion in ["centrality", "size"]
        assert faces is not None and len(faces) > 0

        if criterion == "centrality":
            img_center = np.array([img.shape[0] // 2, img.shape[1] // 2])
            scores = [
                np.linalg.norm(
                    img_center
                    - np.array([(box[0] + box[2]) // 2, (box[1] + box[3]) // 2])
                )
                for box in [face.bbox.astype("int").flatten() for face in faces]
            ]
        elif criterion == "size":
            scores = [
                abs((box[2] - box[0]) * (box[3] - box[1]))
                for box in [face.bbox.astype("int").flatten() for face in faces]
            ]

        if criterion == "centrality":
            best_idx = scores.index(min(scores))
        else:
            best_idx = scores.index(max(scores))

        return faces[best_idx]

    def process_image_single_face(
        self, imgpath: str, draw_keypoints=False
    ):  # Path to image to be processed
        """
        Process a an image considering it has a single face and extract useful features for forensic analysis.
        If more than one face is detected, the largest face will be returned.
        THIS METHOD IS DEPRECATED AND WILL BE REMOVED IN A FUTURE RELEASE. Use process_image instead.
        """
        warnings.warn(
            "process_image_single_face: This method is deprecated and will be removed in a future release.\n"
            "Use the 'process_image' method instead. ",
            DeprecationWarning,
        )
        bgr_img = self._load_image(imgpath)
        return self.process_image(
            bgr_img,
            draw_keypoints=draw_keypoints,
            single_face=True,
            select_single_face_by="size",
        )

    def process_image(
        self,
        imgpath,
        single_face=True,
        draw_keypoints=False,
        select_single_face_by="size",
    ):
        """Process an image assuming one or multiple faces.
        Args:
            - imgpath (str | np.ndarray): Path to the input image or cv2 image array in BGR.
            - draw_keypoints (bool): If set to True, draw the keypoints on the aligned face.
            - single_face (bool): If set to True, assume the image may contain more than one face.
            - select_single_face_by (str): criterion to select the face in the image, if more than one face is detected.
                Only applicable when single_face == True. Must be either 'size' or 'centrality'.
        Returns:
            A dictionary containing the following keys:
                - 'keypoints': A 2D numpy array of shape (5, 2) containing the facial keypoints
                        for each face in the image. The keypoints are ordered as follows:
                       left eye, right eye, nose tip, left mouth corner, and right mouth corner.

                - 'ipd': A float representing the inter-pupillary distance for each face in the image.

                - 'embedding': A 1D numpy array of shape (512,) containing the facial embedding
                       for each face in the image.
                       If the concat_emmbeddings == True, keys for each model are used with the names <model_name>_embedding

                - 'bbox': A 1D numpy array of shape (4,) containing the bounding box coordinates for each face
                  in the image. The coordinates are ordered as follows: (xmin, ymin, xmax, ymax).

                - 'aligned_face': A 3D numpy array of shape (H, W, C) in RGB order containing the aligned face image for
                          each face in the image. The image has been cropped and aligned based on the
                          facial keypoints.

                - 'det_score': A float representing the face detection score.

                If the 'extended' is set to True, the dictionary will also contain the following keys:
                - 'gender': A string representing the gender for each face in the image.
                               Possible values are 'M' for male and 'F' for female.

                - 'age': An integer representing the estimated age for each face in the image.

                - 'pitch': A float representing the pitch angle for each face in the image.

                - 'yaw': A float representing the yaw angle for each face in the image.

                - 'roll': A float representing the roll angle for each face in the image.

                - fiqa_score: A float indicating facial image quality.
        """
        if single_face == True:
            warnings.warn(
                "process_image: The return of this function when 'single_face = True' will change in a future release.\n"
                "Instead of returning a dict, it will return a list (with one dict). ",
                FutureWarning,
            )
        bgr_img = self._load_image(imgpath)
        faces = self.detectmodel.get(bgr_img)
        if len(faces) == 0:
            return []

        if single_face:
            faces = [
                self._get_best_face(bgr_img, faces, criterion=select_single_face_by)
            ]

        results = []
        for face in faces:
            bgr_aligned_face = face_align.norm_crop(bgr_img, face.kps)
            embeddings, fiqa_score = self._compute_embeddings(bgr_aligned_face)
            if draw_keypoints:
                bgr_aligned_face = self._draw_keypoints_on_aligned_face(
                    bgr_aligned_face, face.kps
                )
            result = self._assemble_result(
                face, bgr_aligned_face, embeddings, fiqa_score
            )
            results.append(result)

        return results if not single_face else results[0]

    def _draw_keypoints_on_aligned_face(self, bgr_aligned_face, keypoints):
        aligned_face = bgr_aligned_face.copy()
        M = face_align.estimate_norm(keypoints)
        aligned_kps = transform_keypoints(keypoints=keypoints, M=M)
        annotated_aligned_face = annotate_img_with_kps(
            aligned_face, kps=aligned_kps, color="green"
        )
        return annotated_aligned_face

    def _compute_embeddings(self, bgr_aligned_face):
        """Computes embeddings and FIQA score for an aligned face."""
        img_to_input = self._to_input_ada(bgr_aligned_face)
        embeddings = []
        for rec_ort in self.rec_inference_sessions:
            model_inputs = {rec_ort.get_inputs()[0].name: img_to_input}
            model_output = rec_ort.run(None, model_inputs)
            if (
                len(model_output) == 2
            ):  # model output in the form of normed_embedding, norm
                embedding = model_output[0].flatten() * model_output[1].flatten()[0]
            else:  # model output in the form of embedding
                embedding = model_output[0].flatten()
            embeddings.append(embedding)

        fiqa_score = None
        if self.extended:
            _, fiqa_score = self.ort_fiqa.run(
                None, {self.ort_fiqa.get_inputs()[0].name: img_to_input}
            )

        return (
            np.concatenate(embeddings) if self.concat_embeddings else embeddings,
            fiqa_score[0][0] if fiqa_score is not None else None,
        )

    def _assemble_result(self, face, bgr_aligned_face, embeddings, fiqa_score):
        """Assembles the result dictionary for a face."""
        ret = {
            "ipd": np.linalg.norm(face.kps[0] - face.kps[1]),
        }

        if self.extended:
            ret.update(
                {
                    "fiqa_score": fiqa_score,
                    "gender": "M" if face.gender == 1 else "F",
                    "age": face.age,
                    "yaw": face.pose[1],
                    "pitch": face.pose[0],
                    "roll": face.pose[2],
                }
            )

        ret.update(
            {
                "det_score": face.det_score,
                "keypoints": face.kps,
                "bbox": face.bbox.astype("int"),
            }
        )
        if self.concat_embeddings:
            ret["embedding"] = embeddings
        else:
            for model_name, embedding in zip(self.models, embeddings):
                ret[f"embedding_{model_name}"] = embedding

        ret["aligned_face"] = cv2.cvtColor(bgr_aligned_face, cv2.COLOR_BGR2RGB)
        return ret

    def _load_image(self, imgpath):
        """Load image from file path or return the array if already loaded."""
        return cv2.imread(imgpath) if isinstance(imgpath, str) else imgpath.copy()

    def process_image_multiple_faces(
        self, imgpath: str, draw_keypoints=False  # Path to image to be processed
    ):
        """
        Process an image with one or multiple faces.
        THIS METHOD IS DEPRECATED AND WILL BE REMOVED IN A FUTURE RELEASE. Use process_image instead.
        """
        warnings.warn(
            "process_image_multiple_faces: This method is deprecated and will be removed in a future release.\n"
            "Use the 'process_image' method instead.",
            DeprecationWarning,
        )
        bgr_img = self._load_image(imgpath)
        return self.process_image(
            bgr_img, draw_keypoints=draw_keypoints, single_face=False
        )

    def build_mosaic(
        self,
        img_path_list,
        mosaic_shape,
        border=0.03,
        save_to=None,
        draw_keypoints=False,
    ):
        """
        Build a rectangular mosaic of the aligned faces.
        Based on the imutils build_montages function.

        Parameters:
            img_path_list: list of paths to image files
            mosaic_shape: tuple of integers, (n_cols, n_rows)
            border: float, percent of image to use as white border

        Returns:
            cv2 BGR image with mosaic
        """
        assert mosaic_shape is not None
        top = int(border * self.IMG_SIZE[0])  # shape[0] = rows
        bottom = top
        left = int(border * self.IMG_SIZE[1])  # shape[1] = cols
        right = left

        imgs = []
        list_of_arrays = False
        for img in img_path_list:
            if type(img) != str:  # image array passed as argument
                list_of_arrays = True
            ret = self.process_image(
                img, draw_keypoints=draw_keypoints, single_face=True
            )
            if len(ret) > 0:
                img = cv2.cvtColor(ret["aligned_face"], cv2.COLOR_RGB2BGR)
                img = cv2.copyMakeBorder(
                    img,
                    top=top,
                    bottom=bottom,
                    left=left,
                    right=right,
                    borderType=cv2.BORDER_CONSTANT,
                    value=(255, 255, 255),
                )
                imgs.append(img)
        mosaic = build_montages(
            imgs,
            image_shape=(
                int(self.IMG_SIZE[0] * (1 + 2 * border)),
                int(self.IMG_SIZE[1] * (1 + 2 * border)),
            ),
            montage_shape=mosaic_shape,
        )[0]
        if list_of_arrays:
            warnings.warn(
                "A list of arrays was passed as argument. Make sure image arrays are in BGR format.",
                Warning,
            )
        if save_to is not None:
            cv2.imwrite(save_to, mosaic)
        return mosaic

# %% ../nbs/00_forensicface.ipynb 17
@patch
def compare(self: ForensicFace, img1path: str, img2path: str):
    """
    Compares the similarity between two face images based on their embeddings.

    Parameters:
        - img1path (str): Path to the first image file
        - img2path (str): Path to the second image file

    Returns:
        A float representing the similarity score between the two faces based on their embeddings.
        The score ranges from -1.0 to 1.0, where 1.0 represents a perfect match and -1.0 represents a complete mismatch.
    """
    img1data = self.process_image(img1path, single_face=True)
    assert len(img1data) > 0, f"No face detected in {img1path}"
    img2data = self.process_image(img2path, single_face=True)
    assert len(img2data) > 0, f"No face detected in {img2path}"
    assert self.concat_embeddings == True

    return np.dot(img1data["embedding"], img2data["embedding"]) / (
        np.linalg.norm(img1data["embedding"]) * np.linalg.norm(img2data["embedding"])
    )

# %% ../nbs/00_forensicface.ipynb 20
@patch
def aggregate_embeddings(self: ForensicFace, embeddings, weights=None, method="mean"):
    """
    Aggregates multiple embeddings into a single embedding.

    Args:
        embeddings (numpy.ndarray): A 2D array of shape (num_embeddings, embedding_dim) containing the embeddings to be
            aggregated.
        weights (numpy.ndarray, optional): A 1D array of shape (num_embeddings,) containing the weights to be assigned
            to each embedding. If not provided, all embeddings are equally weighted.

        method (str, optional): choice of agregating based on the mean or median of the embeddings. Possible values are
            'mean' and 'median'.

    Returns:
        numpy.ndarray: A 1D array of shape (embedding_dim,) containing the aggregated embedding.
    """
    if weights is None:
        weights = np.ones(embeddings.shape[0], dtype="int")
    assert embeddings.shape[0] == weights.shape[0]
    assert method in ["mean", "median"]
    if method == "mean":
        return np.average(embeddings, axis=0, weights=weights)
    else:
        weighted_embeddings = np.array([w * e for w, e in zip(weights, embeddings)])
        return np.median(weighted_embeddings, axis=0)

# %% ../nbs/00_forensicface.ipynb 21
@patch
def aggregate_from_images(
    self: ForensicFace, list_of_image_paths, method="mean", quality_weight=False
):
    """
    Given a list of image paths, this method returns the average embedding of all faces found in the images.

    Args:
        list_of_image_paths (List[str]): List of paths to images.
        method (str, optional): choice of agregating based on the mean or median of the embeddings. Possible values are
            'mean' and 'median'.
        quality_weight (boolean, optional): If True, use the FIQA(L) score as a weight for aggregation.

    Returns:
        Union[np.ndarray, List]: If one or more faces are found, returns a 1D numpy array of shape (512,) representing the
        average embedding. Otherwise, returns an empty list.
    """
    if quality_weight:
        assert (
            self.extended == True
        ), "You must initialize ForensicFace with extended = True"
    assert self.concat_embeddings == True
    embeddings = []
    weights = []
    for imgpath in list_of_image_paths:
        d = self.process_image(imgpath, single_face=True)
        if len(d) > 0:
            embeddings.append(d["embedding"])
            weights.append(d["fiqa_score"] if quality_weight == True else 1.0)
    if len(embeddings) > 0:
        return self.aggregate_embeddings(
            np.array(embeddings), method=method, weights=np.array(weights)
        )
    else:
        return []

# %% ../nbs/00_forensicface.ipynb 25
@patch
def _get_extended_bbox(self: ForensicFace, bbox, frame_shape, margin_factor):
    """
    Computes and returns the bounding box with extended margins.

    Parameters:
        bbox (ndarray): The bounding box coordinates (startX, startY, endX, endY).
        frame_shape (tuple): The shape of the video frame (height, width, channels).
        margin_factor (float): The factor to be applied for computing the margin.

    Returns:
        A list with the coordinates of the extended bounding box (startX_out, startY_out, endX_out, endY_out).
    """
    # add a margin on the bounding box
    (startX, startY, endX, endY) = bbox.astype("int")
    (h, w) = frame_shape[:2]
    out_width = (endX - startX) * margin_factor
    out_height = (endY - startY) * margin_factor

    startX_out = int((startX + endX) / 2 - out_width / 2)
    endX_out = int((startX + endX) / 2 + out_width / 2)
    startY_out = int((startY + endY) / 2 - out_height / 2)
    endY_out = int((startY + endY) / 2 + out_height / 2)

    # tests if the output bbox coordinates are out of frame limits
    if startX_out < 0:
        startX_out = 0
    if endX_out > int(w):
        endX_out = int(w)
    if startY_out < 0:
        startY_out = 0
    if endY_out > int(h):
        endY_out = int(h)
    return [startX_out, startY_out, endX_out, endY_out]


@patch
def extract_faces(
    self: ForensicFace,
    video_path: str,  # path to video file
    dest_folder: str = None,  # folder used to save extracted faces. If not provided, a new folder with the video name is created
    every_n_frames: int = 1,  # skip some frames
    margin: float = 2.0,  # margin to add to each face, w.r.t. detected bounding box
    start_from: float = 0.0,  # seconds after video start to begin processing
    export_metadata: bool = False,  # if True, export facial keypoints, bounding box, ipd, fiqa_score, pitch, yaw, roll, and embedding
):
    """
    Extracts faces from a video and saves them as individual images.

    Parameters:
        video_path (str): The path to the input video file.
        dest_folder (str, optional): The path to the output folder. If not provided, a new folder with the same name as the input video file is created.
        every_n_frames (int, optional): Extract faces from every n-th frame. Default is 1 (extract faces from all frames).
        margin (float, optional): The factor by which the detected face bounding box should be extended. Default is 2.0.
        start_from (float, optional): The time point (in seconds) after which the video frames should be processed. Default is 0.0.

    Returns:
        The number of extracted faces.
    """
    import pandas as pd

    if dest_folder is None:
        dest_folder = os.path.splitext(video_path)[0]

    os.makedirs(dest_folder, exist_ok=True)

    # initialize video stream from file
    vs = cv2.VideoCapture(video_path)
    fps = vs.get(cv2.CAP_PROP_FPS)
    start_frame = int(fps * start_from)

    # seek to starting frame
    vs.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    current_frame = start_frame
    nfaces = 0
    if export_metadata:
        metadata = []
    with tqdm(
        total=total_frames,
        bar_format="Frames processed: {n}/{total} | Time elapsed: {elapsed}",
    ) as pbar:
        while True:

            ret, frame = vs.read()

            if not ret:
                break

            current_frame = current_frame + 1
            continue

        vs.set(cv2.CAP_PROP_POS_FRAMES, current_frame)
        ret, frame = vs.read()

            # faces = self.detectmodel.get(frame)
            rets = self.process_image(frame, single_face=False)
            for i, ret in enumerate(rets):
                startX, startY, endX, endY = ret["bbox"]
                faceW = endX - startX
                faceH = endY - startY
                outBbox = self._get_extended_bbox(
                    ret["bbox"], frame.shape, margin_factor=margin
                )
                # export the face (with added margin)
                face_crop = frame[outBbox[1] : outBbox[3], outBbox[0] : outBbox[2]]
                face_img_path = os.path.join(
                    dest_folder, f"frame_{current_frame:07}_face_{i:02}.png"
                )
                cv2.imwrite(face_img_path, face_crop)
                if export_metadata:
                    metadata.append(
                        {
                            **{"frame": current_frame, "face": i},
                            **{
                                k: v
                                for k, v in ret.items()
                                if k not in ["det_score", "aligned_face"]
                            },
                        }
                    )
                nfaces += 1
            pbar.update(1)
    vs.release()
    if export_metadata:
        pd.DataFrame(metadata).to_json(
            os.path.join(
                dest_folder,
                os.path.splitext(os.path.basename(video_path))[0] + ".jsonl",
            ),
            lines=True,
            orient="records",
        )
    return nfaces

# %% ../nbs/00_forensicface.ipynb 29
@patch
def process_aligned_face_image(self: ForensicFace, rgb_aligned_face: np.ndarray):
    assert rgb_aligned_face.shape == (*self.IMG_SIZE, 3)
    bgr_aligned_face = rgb_aligned_face[..., ::-1].copy()
    embeddings, fiqa_score = self._compute_embeddings(bgr_aligned_face)

    if self.concat_embeddings:
        ret = {"embedding": embeddings}
    else:
        ret = {}
        for model_name, embedding in zip(self.models, embeddings):
            ret["embedding_" + model_name] = embedding
    if self.extended:
        ret = {**ret, **{"fiqa_score": fiqa_score}}
    return ret
