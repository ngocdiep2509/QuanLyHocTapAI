-- 1. Tạo Database (Nếu chưa có)
IF NOT EXISTS(SELECT * FROM sys.databases WHERE name = 'DatabaseAI')
BEGIN
    CREATE DATABASE DatabaseAI;
END
GO

USE DatabaseAI;
GO

-- 2. Tạo bảng SinhVien
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='SinhVien' and xtype='U')
CREATE TABLE SinhVien (
    SinhVienID VARCHAR(20) PRIMARY KEY,
    HoTen NVARCHAR(100)
);
GO

-- 3. Tạo bảng MonHoc
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='MonHoc' and xtype='U')
CREATE TABLE MonHoc (
    MonHocID VARCHAR(20) PRIMARY KEY,
    TenMonHoc NVARCHAR(100),
    DiemKho FLOAT DEFAULT 3.0 -- Điểm khó mặc định
);
GO

-- 4. Tạo bảng LichTrinh (Quan trọng nhất)
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='LichTrinh' and xtype='U')
CREATE TABLE LichTrinh (
    LichTrinhID VARCHAR(20) PRIMARY KEY,
    SinhVienID VARCHAR(20),
    MonHocID VARCHAR(20),
    TieuDe NVARCHAR(200),
    LoaiSuKien VARCHAR(50), -- VD: 'DEADLINE'
    ThoiGianBatDau DATETIME,
    ThoiGianKetThuc DATETIME,
    MucDoQuanTrong INT,
    DiemUuTien FLOAT,
    
    -- Khóa ngoại (Optional - để đảm bảo dữ liệu chuẩn)
    FOREIGN KEY (SinhVienID) REFERENCES SinhVien(SinhVienID),
    FOREIGN KEY (MonHocID) REFERENCES MonHoc(MonHocID)
);
GO