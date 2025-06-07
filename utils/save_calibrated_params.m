% 假设 cameraParameters 对象已经在你的 MATLAB 工作空间中

% 1. 获取相机内参对象
intrinsics = cameraParams.Intrinsics;

% 2. 获取内参矩阵 K
% MATLAB 的 intrinsics.IntrinsicMatrix 存储的是 K 的转置
cameraMatrix = intrinsics.IntrinsicMatrix';
% 如果你的 MATLAB 版本较新，可以直接用 intrinsics.K，它通常就是我们理解的K，但仍建议确认或使用转置：
% cameraMatrix = intrinsics.K'; % 双重检查 K 是否需要转置

% 3. 获取畸变系数
% RadialDistortion 通常是 [k1, k2] 或 [k1, k2, k3]
% TangentialDistortion 通常是 [p1, p2]
radialDist = intrinsics.RadialDistortion;
tangentialDist = intrinsics.TangentialDistortion;

% 组合畸变系数，使其符合 OpenCV 等库常用的顺序 (k1, k2, p1, p2, k3, k4, k5, k6 ...)
% 你需要根据你在标定时选择的畸变模型来确定实际的系数数量和顺序。
% 常见的模型是包含 k1, k2, p1, p2, k3。
numRadial = length(radialDist);
distCoeffs = zeros(1, 5); % 先假设最多5个畸变系数 (k1,k2,p1,p2,k3)
                          % OpenCV 可以处理更多，如k4,k5,k6

if numRadial >= 1
    distCoeffs(1) = radialDist(1); % k1
end
if numRadial >= 2
    distCoeffs(2) = radialDist(2); % k2
end
if ~isempty(tangentialDist)
    distCoeffs(3) = tangentialDist(1); % p1
    distCoeffs(4) = tangentialDist(2); % p2
end
if numRadial >= 3
    distCoeffs(5) = radialDist(3); % k3
end

% 如果你的模型有更多系数 (k4, k5, k6)，你需要相应地扩展 distCoeffs
% 例如，如果 cameraParameters.EstimateTangentialDistortion 为 false，则 tangentialDist 为空
% 如果 cameraParameters.NumRadialDistortionCoefficients 为 2，则 radialDist 只有 k1, k2

% 确保 distCoeffs 是一个行向量或列向量，根据你的 Python 代码的期望调整
% 通常，NumPy 读取后作为一维数组处理。
distCoeffs = distCoeffs(:)'; % 确保是行向量

% 打印检查
disp('Camera Matrix (K):');
disp(cameraMatrix);
disp('Distortion Coefficients (dist_coeffs):');
disp(distCoeffs);

% 4. 保存到 .mat 文件
% 为了确保 Python scipy.io.loadmat 能更好地读取，可以考虑使用 -v7 或 -v7.3 参数，
% 但通常默认版本也能很好地工作。
save('matlab_calibration_data.mat', 'cameraMatrix', 'distCoeffs');
disp('相机参数已保存到 matlab_calibration_data.mat');

% 你也可以把整个 cameraParameters 对象也存进去，以备后续在 MATLAB 中使用
% save('matlab_calibration_data_full.mat', 'cameraParameters', 'cameraMatrix', 'distCoeffs');