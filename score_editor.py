import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import json
import os
from PIL import Image, ImageDraw, ImageTk

FONT_TYPE = "meiryo"

class ScoreEditor(ctk.CTk): 
    def __init__(self):
        super().__init__()
        self.title("SDVX Score Editor")
        
        # --- 基本定義 ---
        self.max_lanes = 6 #レーンの数
        self.lane_width = 50 #レーンの横幅
        self.sixteen_interval = 18 #16分音符の線の間隔
        self.twelve_interval = 24 #12分の間隔
        self.measure_height = self.sixteen_interval * 16 # 1小節の高さ
        self.extra_padding = 10 # 見やすくするための余白
        self.all_height = 32000 + self.extra_padding #全体の高さ
        
        # 左側の小節番号用マージン
        self.margin_left = 40 
        
        #グリッド線
        self.current_tile = self.create_grid_tile(16)
        

        # ウィンドウ幅をマージン分広げる
        canvas_w = self.lane_width * self.max_lanes + self.margin_left
        self.geometry(f"{canvas_w + 100}x600")
        
        self.notes_data = [] #譜面データを入れるリスト

        #jsonファイル読み込みフレームの設定
        self.read_file_frame = ReadFileFrame(master=self,header_name = "jsonファイル読み込み")
        self.read_file_frame.pack()

        #スクロールのフレーム　
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=canvas_w + 40, height=400)
        self.scroll_frame.pack(pady=20)

        self.canvas = ctk.CTkCanvas(
            self.scroll_frame, 
            width=canvas_w, 
            height=self.all_height,
            bg="#1a1a1a", 
            highlightthickness=0
        )
        self.canvas.pack()

        self.draw_score_structure()
        
        self.button_frame = ButtonFrame(master=self,header_name = "ButtonFrame")
        self.button_frame.pack()
        
        self.data_save_frame = DataSaveFrame(master=self,header_name = "DataSaveFrame")
        self.data_save_frame.pack(pady=20)

        # 閉じるボタン
        #self.close_btn = ctk.CTkButton(
            #self, 
            #text="閉じる", 
            #fg_color="#444",      # 少し目立たない色に
            #hover_color="#666", 
            #command=self.destroy  # ウィンドウを閉じる
        #)
        #self.close_btn.pack(side="left", padx=10)
        
        # 単押し(Chip)とロング(Long)の分岐を管理するために、直接 add_note を呼ばず管理関数を通します
        self.canvas.bind("<Button-1>", self.on_canvas_click)  # クリック時
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)   # ドラッグ中
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release) # 離した時

        # ロングノーツ用の一時変数
        self.long_start_y = None
        self.preview_note_id = None

        self.update_grid()
        # 起動時に一番下へスクロール（100ms待ってから実行）
        self.after(100, self.scroll_to_bottom)
        

    def create_grid_tile(self,divisions):
        """1小節分のグリッド画像を生成"""
        w = self.max_lanes * self.lane_width
        h = self.measure_height
        
        img = Image.new("RGBA", (w, h), (26, 26, 26, 255))
        draw = ImageDraw.Draw(img)

        # レーン背景
        draw.rectangle([0, 0, self.lane_width, h], fill=(10, 42, 77, 255)) 
        draw.rectangle([(self.max_lanes-1)*self.lane_width, 0, w, h], fill=(77, 10, 26, 255)) 

        # 縦線
        for i in range(self.max_lanes + 1):
            x = i * self.lane_width
            color = (136, 136, 136, 255) if i == 0 or i == self.max_lanes else (68, 68, 68, 255)
            draw.line([(x, 0), (x, h)], fill=color, width=1)

        # 横線
        interval = h / divisions
        for j in range(divisions):
            y = j * interval
            color = (100, 100, 100, 255) if j == 0 else (51, 51, 51, 255)
            draw.line([(0, y), (w, y)], fill=color, width=1)

        return ImageTk.PhotoImage(img, master=self)
    
    
    def update_grid(self, choice=None):
        """16分か12分かのグリッド線切替え"""
        # 既存のグリッド（"grid"タグがついたもの）を全削除
        self.canvas.delete("grid")
        
        # 選択されたモードに合わせてタイルを作成
        mode = self.button_frame.notes_interval_box.get()
        divisions = 16 if mode == "16分" else 12
        self.current_tile = self.create_grid_tile(divisions)
        
        # グリッドの再描画
        self.draw_score_structure()
        
        # グリッドをノーツより背面に移動
        self.canvas.tag_lower("grid")


    def draw_score_structure(self):
        """タイル画像と小節番号を配置"""
        # 本来の譜面の底（余白より上の位置）を定義
        base_y = self.all_height - self.extra_padding
        
        num_measures = (self.all_height - self.extra_padding) // self.measure_height
        
        for m in range(num_measures):
            y_pos = m * self.measure_height
            
            # 1. タイル画像をマージン分右にずらし、譜面の底から順に上に配置
            # base_y を基準にする
            self.canvas.create_image(self.margin_left,
                                     base_y - y_pos,
                                     image=self.current_tile,
                                     anchor="sw",
                                     tags = "grid")
            
            # 2. 小節番号の描画
            measure_no = m + 1
            # 小節の底の位置（base_y基準）
            text_y = base_y - y_pos
            
            self.canvas.create_text(
                self.margin_left - 10,
                text_y,
                text=f"{measure_no:d}",
                fill="#888",
                font=("Arial", 10, "bold"),
                anchor="se",
                tags = "grid"
            )
            
            
    def on_canvas_click(self, event):
        """マウスを押したときの処理"""
        if event.x < self.margin_left: return
        
        lane = (event.x - self.margin_left) // self.lane_width
        base_y = self.all_height - self.extra_padding
        # クリックした位置の「譜面底からの距離」
        click_timing = base_y - event.y
        
        note_type  = self.button_frame.note_type_box.get()
        
        # --- 1. 削除判定（当たり判定） ---
        if note_type == "BT_Long" or note_type == "FX_Long":
            existing_note = None
            for note in self.notes_data:
             # レーンの判定
                lane_match = False
                if note["type"] == note_type:
                    if note["type"] == "FX_Long" and note["lane"] <= lane <= note["lane"] + 1:
                        # FXは2レーン分（1-2 または 3-4）
                        lane_match = True
                    elif note["type"] == "BT_Long" and note["lane"] == lane:
                        # BTやつまみはそのまま
                        lane_match = True
            
                if lane_match:
                    # 縦方向の判定 (判定タイミングから長さ分の上までの範囲)
                    # チップノーツでも少し余裕（10px程度）を持たせると消しやすいです
                    note_bottom = note["timing"]
                    note_top = note["timing"] + max(note.get("length", 0), 10)
                
                    if note_bottom <= click_timing <= note_top:
                        existing_note = note
                        break

            if existing_note:
                # 見つかったら削除
                self.canvas.delete(existing_note["id"])
                self.notes_data.remove(existing_note)
                #print(f"Deleted: Lane {existing_note["lane"]}, Timing {existing_note["timing"]}")
                self.is_deleting = True # 削除した瞬間に新しいノーツが作られないようにするフラッグ
                return
        
        self.is_deleting = False

        # --- 2. 設置処理の振り分け ---
        #長押し
        if note_type == "BT_Long" or note_type == "FX_Long":
            self.long_start_y = event.y
            self.preview_note_id = None

        else: #それ以外
            self.notes_interval_check(event)
            
            
    def on_canvas_drag(self, event):
        """ドラッグ中のプレビュー描画（Longモードのみ）"""
        # 削除中の場合は何もしない
        #if getattr(self, "is_deleting", False): return
        
        if (self.button_frame.note_type_box.get() == "BT_Long" or self.button_frame.note_type_box.get() == "FX_Long") and self.long_start_y is not None:
            self.draw_long_preview(event)
            

    def on_canvas_release(self, event):
        """マウスを離したときの確定処理（Longモードのみ）"""
        # 削除中の場合は何もしない
        #if getattr(self, "is_deleting", False): 
           # self.is_deleting = False # 次回のためにリセット
            #return
        
        if (self.button_frame.note_type_box.get() == "BT_Long" or self.button_frame.note_type_box.get() == "FX_Long") and self.long_start_y is not None:
            self.add_long_note(event)
            self.long_start_y = None
            self.preview_note_id = None
        
                   
    def notes_interval_check(self,event):
        notes_interval = self.button_frame.notes_interval_box.get()
        
        if notes_interval == "16分":
            self.add_note(event,self.sixteen_interval)
            
        elif notes_interval == "12分":
            self.add_note(event,self.twelve_interval)
            
            
    def add_note(self, event,interval):
        
        # マージン分を差し引いてレーンを判定
        if event.x < self.margin_left:
            return 

        lane = (event.x - self.margin_left) // self.lane_width
        
        # 0小節目の線のY座標を取得
        base_y = self.all_height - self.extra_padding
        
        # 底からの距離を計算して、そこから16分の間隔で吸着させる
        dist_from_base = base_y - event.y
        snapped_dist = round(dist_from_base / interval) * interval
        
        # 実際のキャンバス座標に変換
        snap_timing = base_y - snapped_dist
        
        #ノーツの種類
        note_type = self.button_frame.note_type_box.get()
        
        # 2. ノーツの高さを定義
        note_h = 8 
        note_id = None
        
        if 0 <= lane < self.max_lanes:
            
            # すでに同じレーン・同じタイミングのノーツがあるか探す
            existing_note = None
            
            for note in self.notes_data:
                if abs(note["timing"] - (base_y - snap_timing)) < 1:
                    #btの削除
                    if note["type"] == note_type and note["lane"] == lane :
                        existing_note = note
                        break
                    
                    #fxの削除
                    elif note["type"] == note_type and  note["type"] == "FX":
                        # 左FX(1,2)か右FX(3,4)かを判定
                        is_left_fx = (1 <= lane <= 2 and note["lane"] == 1)
                        is_right_fx = (3 <= lane <= 4 and note["lane"] == 3)
                        if is_left_fx or is_right_fx:
                            existing_note = note
                            break
                        
            # もし見つかったら削除して終了
            if existing_note:
                # キャンバスから図形を消す
                self.canvas.delete(existing_note["id"])
                # リストからデータを消す
                self.notes_data.remove(existing_note)
                #print(f"Deleted:Type {note_type}, Lane {existing_note["lane"]}, Timing {existing_note["timing"]}")
                return # ここで処理を終わらせる（新しく置かない）
                 
            # FXノーツを設置する処理
            if note_type == "FX" and 1 <= lane <= 4:
                fx_lane = 1 if lane <= 2 else 3 # 1-2なら1(左)、3-4なら3(右)を基準にする
                x_start = self.margin_left + (fx_lane * self.lane_width) + 2
                x_end = x_start + (self.lane_width * 2) - 4
                points = [x_start,snap_timing - note_h,x_end, snap_timing]
                
                note_id = self.canvas.create_rectangle(
                    points, 
                    fill="#ff8800", # FXはオレンジ色
                    outline="white", 
                    width=1,
                    tags="fx_note" # タグ付け
                )
 
                self.notes_data.append({"type":note_type,"lane": lane, "timing": base_y - snap_timing,"id": note_id,"points":points})
                #print({"type":note_type,"lane": lane, "timing": base_y - snap_timing,"id": note_id,"points":points})

                
                #存在チェックを入れる ---
                if self.canvas.find_withtag("bt_note"):
                    # bt_note が存在する場合のみ、その下に送る
                    self.canvas.tag_lower(note_id, "bt_note")
                else:
                    # bt_note がない場合は、背景グリッド(grid)より上にくるように調整
                    self.canvas.tag_raise(note_id, "grid")
            
            #btの配置
            elif note_type == "BT" and 1 <= lane <= 4:
                # 描画位置の計算
                x_start = self.margin_left + (lane * self.lane_width) + 2
                x_end = x_start + self.lane_width - 4
                points = [x_start,snap_timing - note_h,x_end, snap_timing]
            
                note_id = self.canvas.create_rectangle(
                    points, 
                    fill="white", outline="white", width=1,
                    tags="bt_note" # タグ付け
                    )
                
                self.notes_data.append({"type":note_type,"lane": lane, "timing": base_y - snap_timing,"id": note_id,"points":points})
                #print({"type":note_type,"lane": lane, "timing": base_y - snap_timing,"id": note_id,"points":points})
   
            elif note_type == "Tumami_Blue_Left" or note_type == "Tumami_Blue_Right":
                if lane == 0:    # 0 または 5レーン：つまみ（矢印）
                    # 描画位置の計算
                    x_start = self.margin_left + (lane * self.lane_width) + 2
                    x_end = x_start + self.lane_width - 4
                    if note_type == "Tumami_Blue_Left":
                        #左向きの三角形
                        points = [
                            x_start, snap_timing - (note_h / 2), # 先端（左）
                            x_end, snap_timing - note_h,         # 右上
                            x_end, snap_timing                   # 右下
                            ]
                        
                    elif note_type == "Tumami_Blue_Right":
                        # 右つまみ：右向きの三角形
                        points = [
                            x_end, snap_timing - (note_h / 2),   # 先端（右）
                            x_start, snap_timing - note_h,       # 左上
                            x_start, snap_timing                 # 左下
                            ]
                
                    note_id = self.canvas.create_polygon(
                        points, 
                        fill="#00ffff", 
                        outline="white", 
                        width=1
                        )
                    # データには「判定タイミング（底辺）」の座標を保存
                    self.notes_data.append({"type":note_type,"lane": lane, "timing": base_y - snap_timing,"id": note_id,"points":points})
                    #print({"type":note_type,"lane": lane, "timing": base_y - snap_timing,"id": note_id,"points":points}
                
            elif note_type == "Tumami_Red_Left" or note_type == "Tumami_Red_Right":
                if lane == 5:
                    # 描画位置の計算
                    x_start = self.margin_left + (lane * self.lane_width) + 2
                    x_end = x_start + self.lane_width - 4
                    if note_type == "Tumami_Red_Left":
                        #左向きの三角形
                        points = [
                            x_start, snap_timing - (note_h / 2), # 先端（左）
                            x_end, snap_timing - note_h,         # 右上
                            x_end, snap_timing                   # 右下
                            ]
                        
                    elif note_type == "Tumami_Red_Right":
                        # 右つまみ：右向きの三角形
                        points = [
                            x_end, snap_timing - (note_h / 2),   # 先端（右）
                            x_start, snap_timing - note_h,       # 左上
                            x_start, snap_timing                 # 左下
                            ]
                
                    note_id = self.canvas.create_polygon(
                        points, 
                        fill="#ff00ff", 
                        outline="white", 
                        width=1
                        )
                    # データには「判定タイミング（底辺）」の座標を保存
                    self.notes_data.append({"type":note_type,"lane": lane, "timing": base_y - snap_timing,"id": note_id,"points":points})
                    #print({"type":note_type,"lane": lane, "timing": base_y - snap_timing,"id": note_id,"points":points})


    def get_snapped_y(self, y_coord):
        """現在の設定に合わせて吸着させたY座標を返す"""
        interval = self.sixteen_interval if self.button_frame.notes_interval_box.get() == "16分" else self.twelve_interval
        base_y = self.all_height - self.extra_padding
        dist = base_y - y_coord
        snapped_dist = round(dist / interval) * interval
        return base_y - snapped_dist
    

    def draw_long_preview(self, event):
        """ドラッグ中に長さを可視化する"""
        if self.preview_note_id:
            self.canvas.delete(self.preview_note_id)

        lane = (event.x - self.margin_left) // self.lane_width
        if not (0 <= lane < self.max_lanes): return

        # 始点と終点をスナップ
        y_start = self.get_snapped_y(self.long_start_y)
        y_end = self.get_snapped_y(event.y)
        
        # 上下関係を整理
        top, bottom = min(y_start, y_end), max(y_start, y_end)
        
        # 描画（FXかBTかで幅を変える）
        note_type = self.button_frame.note_type_box.get()
        if note_type == "FX_Long" and 1 <= lane <= 4:
            fx_lane = 1 if lane <= 2 else 3
            x_s = self.margin_left + (fx_lane * self.lane_width) + 2
            x_e = x_s + (self.lane_width * 2) - 4
            color = "#ff8800"
            
            self.preview_note_id = self.canvas.create_rectangle(
            x_s, top, x_e, bottom, fill=color, outline="white", stipple="gray50" # プレビューなので半透明風に
            )
            
        elif note_type == "BT_Long" and 1 <= lane <= 4:
            x_s = self.margin_left + (lane * self.lane_width) + 2
            x_e = x_s + self.lane_width - 4
            
            self.preview_note_id = self.canvas.create_rectangle(
            x_s, top, x_e, bottom, fill="white", outline="white", stipple="gray50" # プレビューなので半透明風に
            )
            
        else:
            None
            #つまみのときはなにも処理しない
              

    def add_long_note(self, event):
        """ロングノーツをデータとして確定させる"""
        lane = (event.x - self.margin_left) // self.lane_width
        if not (0 <= lane < self.max_lanes): return

        y_start = self.get_snapped_y(self.long_start_y)
        y_end = self.get_snapped_y(event.y)
        
        top, bottom = min(y_start, y_end), max(y_start, y_end)
        length = bottom - top
        if length < 5: return # 短すぎる場合は無視

        note_type = self.button_frame.note_type_box.get()
        base_y = self.all_height - self.extra_padding
        
        # 実際の設置（プレビューではない本番の描画）
        if note_type == "FX_Long" and 1 <= lane <= 4:
            actual_lane = 1 if lane <= 2 else 3
            x_s = self.margin_left + (actual_lane * self.lane_width) + 2
            x_e = x_s + (self.lane_width * 2) - 4
            color = "#ff8800"
            tag = "fx_note"
            
        elif note_type == "BT_Long" and 1 <= lane <= 4:
            actual_lane = lane
            x_s = self.margin_left + (lane * self.lane_width) + 2
            x_e = x_s + self.lane_width - 4
            color = "white"
            tag = "bt_note"

        points = [x_s, top, x_e, bottom]
        note_id = self.canvas.create_rectangle(
            points, fill=color, outline="white", tags=tag
        )
        
        # データの保存（lengthを追加）
        self.notes_data.append({
            "type": note_type,
            "lane": actual_lane, 
            "timing": base_y - bottom, # 底辺
            "length": length, 
            "id": note_id,
            "points":points
        })
        
        #print({"type":note_type,"lane": actual_lane, "timing": base_y - bottom,"length": length,"id": note_id,"points":points})
        
        if self.preview_note_id:
            self.canvas.delete(self.preview_note_id)
            self.preview_note_id = None
        
        # FXならレイヤー移動
        if tag == "fx_note":
            if self.canvas.find_withtag("bt_note"):
                self.canvas.tag_lower(note_id, "bt_note")
                

    def save_to_json(self):
        result_notes_data = sorted(self.notes_data, key=lambda x: x["timing"])
        # "id" 以外のキーを抽出して新しい辞書を作る
        result_notes_data = [
            {k: v for k, v in note.items() if k != "id"} 
            for note in result_notes_data
            ]
        
        file_name = self.data_save_frame.json_file_name_box.get() + ".json"
        
        with open(file_name, "w", encoding="utf-8") as f:
            # indent=4 をつけると人間が見やすくなります
            json.dump(result_notes_data, f, indent=4, ensure_ascii=False)
        print("Saved to score_data.json")
        
        
    def load_notes(self):
        for note in self.notes_data:
            # 座標リストをそのまま渡して再描画
            if note['type'] == "BT" or note['type'] == "BT_Long":
                note_id = self.canvas.create_rectangle(
                    note["points"], 
                    fill="white", outline="white", width=1,
                    tags="bt_note" # タグ付け
                    )
            
            if note['type'] == "FX" or note['type'] == "FX_Long":
                note_id = self.canvas.create_rectangle(
                    note["points"], 
                    fill="#ff8800", # FXはオレンジ色
                    outline="white", 
                    width=1,
                    tags="fx_note" # タグ付け
                )
            
            if note['type'] == "Tumami_Blue_Left" or note['type'] == "Tumami_Blue_Right":
                note_id = self.canvas.create_polygon(
                        note["points"], 
                        fill="#00ffff", 
                        outline="white", 
                        width=1
                        )
            
            if note['type'] == "Tumami_Red_Left" or note['type'] == "Tumami_Red_Right":    
                note_id = self.canvas.create_polygon(
                        note["points"], 
                        fill="#ff00ff", 
                        outline="white", 
                        width=1
                        )
            
            note["id"] = note_id
 
 
    def scroll_to_bottom(self):
        """スクロールバーを一番下に移動させる"""
        # CTkScrollableFrameの内部キャンバスを操作して位置を1.0（100%）にする
        self.scroll_frame._parent_canvas.yview_moveto(1.0)
        
        
class ReadFileFrame(ctk.CTkFrame):
    
    def __init__(self,master,header_name="ReadFileFrame", **kwargs):
        super().__init__(master=master,**kwargs)
        self.app = master
        
        #メンバ関数の設定
        self.fonts = (FONT_TYPE,12)
        self.header_name = header_name
        
        #フォームのセットアップをする
        self.setup_form()
        
        
    def setup_form(self):
        #レイアウト設定
        self.grid_rowconfigure(0,weight=1) #行方向
        self.grid_columnconfigure(0,weight=1) #列方向
        
        #jsonファイルパスを指定するテキストボックス
        self.json_textbox = ctk.CTkEntry(master=self,placeholder_text="jsonファイルを読み込む",width=250,font=self.fonts)
        self.json_textbox.grid(row=0,column=0,padx=10,pady=(0,10),sticky="ew")
        
        #jsonファイル選択ボタン
        self.json_select = ctk.CTkButton(master=self,fg_color="transparent",border_width=2,width = 60,text_color=("gray10","#DCE4EE"),
                                                     command=lambda:self.json_select_callback(self.json_textbox),text="ファイル選択",font=self.fonts)
        self.json_select.grid(row=0,column=1,padx=2,pady=(0,10))
        
        #ロードボタン
        self.button_load = ctk.CTkButton(master=self,width = 60,command=self.button_load_callback,text="読み込む",font=self.fonts)
        self.button_load.grid(row=0,column=2,padx=2,pady=(0,10))
        
    def json_select_callback(self,textbox):
        """
        選択ボタンが押されたときのコールバック。ファイル選択ダイアログを表示する
        """
        #エクスプローラーを表示してファイルを選択する
        file_name = ReadFileFrame.json_file_read()
        
        if file_name is not None:
            #ファイルパスをテキストボックスに記入
            textbox.delete(0,tk.END)
            textbox.insert(0,file_name)
            
            
    def button_load_callback(self):
        """
        開くボタンが押されたときのコールバック。
        """
        json_file_path = self.json_textbox.get()
        try:
            with open(json_file_path, "r", encoding="utf-8") as f:
                self.master.notes_data = json.load(f)
                # ここで読み込んだデータをもとにCanvasに再描画する処理が必要
                self.master.load_notes()
        except FileNotFoundError:
            pass


    @staticmethod
    def json_file_read():
        """
        ファイル選択ダイアログを表示する
        """

        current_dir = os.path.abspath(os.path.dirname(__file__))
        file_path = tk.filedialog.askopenfilename(filetypes=[("譜面データファイル","*.json")],initialdir=current_dir)
        
        if len(file_path) != 0:
            return file_path
        else:
            return None
        
class ButtonFrame(ctk.CTkFrame):
    
    def __init__(self,master,header_name="ButtonFrame", **kwargs):
        super().__init__(master=master,**kwargs)
        self.app = master
        
        #メンバ関数の設定
        self.fonts = (FONT_TYPE,12)
        self.header_name = header_name
        
        #フォームのセットアップをする
        self.setup_form()
        
    def setup_form(self):
        #レイアウト設定
        self.grid_rowconfigure(0,weight=1) #行方向
        self.grid_columnconfigure(0,weight=1) #列方向
        
                
        # ノーツの種類切り替え
        self.note_type_box = ctk.CTkComboBox(self, values=["BT", "BT_Long","FX","FX_Long","Tumami_Blue_Left","Tumami_Blue_Right","Tumami_Red_Left","Tumami_Red_Right"])
        self.note_type_box.pack(side = tk.LEFT,padx=5)

        #音符間隔切替え
        self.notes_interval_box = ctk.CTkComboBox(self, values=["16分", "12分"],command=self.master.update_grid)
        self.notes_interval_box.pack(side = tk.LEFT,padx=5)
        

class DataSaveFrame(ctk.CTkFrame):
    
    def __init__(self,master,header_name="DataSaveFrame", **kwargs):
        super().__init__(master=master,**kwargs)
        self.app = master
        
        #メンバ関数の設定
        self.fonts = (FONT_TYPE,12)
        self.header_name = header_name
        
        #フォームのセットアップをする
        self.setup_form()
        
    def setup_form(self):
        #保存するjsonファイル名を指定するテキストボックス
        self.json_file_name_box = ctk.CTkEntry(master=self,placeholder_text="保存するファイル名",width=250,font=self.fonts)
        self.json_file_name_box.grid(row=0,column=0,padx=10,pady=(0,10),sticky="ew")
        self.save_btn = ctk.CTkButton(self, text="jsonに出力して保存", command=self.master.save_to_json)
        self.save_btn.grid(row=0,column=1,padx=2,pady=(0,10))
        
        
        
if __name__ == "__main__":
    app = ScoreEditor()
    app.mainloop()