import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 中文显示修复
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class BeerGame:
    def __init__(self, initial_inventory=12, holding_cost=0.5, backlog_cost=1.0, max_weeks=50, customer_demand=None):
        self.initial_inventory = initial_inventory
        self.holding_cost = holding_cost
        self.backlog_cost = backlog_cost
        self.max_weeks = max_weeks
        if customer_demand is None:
            self.customer_demand = [4] * 4 + [8] * (max_weeks - 4)
        else:
            self.customer_demand = customer_demand[:max_weeks]

        self.roles_zh = ['零售商', '批发商', '分销商', '制造商']
        self.role_en = ['retailer', 'wholesaler', 'distributor', 'manufacturer']
        self.reset_game()

    def reset_game(self):
        self.current_week = 0
        self.inventory = {role: self.initial_inventory for role in self.role_en}
        self.backlog = {role: 0 for role in self.role_en}
        self.orders_placed = {role: [4] * 4 for role in self.role_en}
        self.production_this_week = 4
        self.weekly_cost = {role: [] for role in self.role_en}
        self.cumulative_cost = {role: 0 for role in self.role_en}

        self.order_pipeline = {role: [0, 0] for role in self.role_en}
        self.shipment_pipeline = {role: [0, 0] for role in self.role_en}

    def place_order(self, role_en: str, amount: int):
        if self.current_week < len(self.orders_placed[role_en]):
            self.orders_placed[role_en][self.current_week] = amount
        else:
            self.orders_placed[role_en].append(amount)

    def set_production(self, amount: int):
        self.production_this_week = max(0, amount)

    def advance_week(self):
        if self.current_week >= self.max_weeks:
            return False

        week = self.current_week

        production = self.production_this_week
        self.shipment_pipeline['distributor'][0] = production

        for i, role_en in enumerate(self.role_en):
            incoming_shipment = self.shipment_pipeline[role_en].pop(0)
            self.shipment_pipeline[role_en].append(0)
            self.inventory[role_en] += incoming_shipment

            # 只有非制造商才有下游需求
            if role_en != 'manufacturer':
                if role_en == 'retailer':
                    demand = self.customer_demand[week]
                else:
                    downstream = self.role_en[i + 1]
                    demand = self.orders_placed[downstream][week] if week < len(self.orders_placed[downstream]) else 4
            else:
                demand = 0  # 制造商没有需求

            to_ship = min(self.inventory[role_en], demand + self.backlog[role_en])
            self.inventory[role_en] -= to_ship
            self.backlog[role_en] = max(0, demand + self.backlog[role_en] - to_ship)

            if role_en != 'manufacturer':
                self.shipment_pipeline[self.role_en[i + 1]][1] = to_ship

            cost = self.holding_cost * max(0, self.inventory[role_en]) + self.backlog_cost * self.backlog[role_en]
            self.weekly_cost[role_en].append(cost)
            self.cumulative_cost[role_en] += cost

        for i in range(3):
            order = self.orders_placed[self.role_en[i]][week]
            self.order_pipeline[self.role_en[i + 1]][1] = order

        self.current_week += 1
        return True


class BeerGameApp:
    def __init__(self, root):
        self.root = root
        self.root.title("啤酒游戏")
        self.root.geometry("1450x900")
        self.root.minsize(1200, 700)

        self.initial_inventory = tk.IntVar(value=12)
        self.holding_cost = tk.DoubleVar(value=0.5)
        self.backlog_cost = tk.DoubleVar(value=1.0)
        self.max_weeks = tk.IntVar(value=50)

        self.game = BeerGame(12, 0.5, 1.0, 50)

        # 底部按钮
        bottom_frame = ttk.Frame(root, relief='raised', padding=20)
        bottom_frame.pack(side='bottom', fill='x')

        self.week_label = ttk.Label(bottom_frame, text="当前周次: 1/50", font=("Helvetica", 20, "bold"))
        self.week_label.pack(side='left', padx=80)

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Huge.TButton", font=("Helvetica", 22, "bold"), padding=30)
        style.map("Huge.TButton", background=[('active', '#004499'), ('!active', '#0055CC')],
                  foreground=[('active', 'white'), ('!active', 'white')])

        self.next_button = ttk.Button(bottom_frame, text="推进下一周", command=self.next_week, style="Huge.TButton")
        self.next_button.pack(side='right', padx=80, ipadx=40, ipady=20)

        # 主内容
        main_container = ttk.Frame(root)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)

        upper_frame = ttk.PanedWindow(main_container, orient='horizontal')
        upper_frame.pack(fill='both', expand=True)

        self.create_config_panel(upper_frame)

        right_frame = ttk.Frame(upper_frame)
        upper_frame.add(right_frame, weight=3)

        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill='both', expand=True)

        self.order_spins = {}
        self.production_spin = None
        self.status_vars = {}

        for role_zh in self.game.roles_zh:
            frame = ttk.Frame(self.notebook)
            self.notebook.add(frame, text=role_zh)
            self.create_role_frame(frame, role_zh)

        overview_frame = ttk.Frame(self.notebook)
        self.notebook.add(overview_frame, text="牛鞭效应总览")
        self.create_overview_frame(overview_frame)

        self.update_all()

    def create_config_panel(self, parent):
        config_frame = ttk.LabelFrame(parent, text="游戏参数配置区", padding=20)
        parent.add(config_frame, weight=1)

        entries = [
            ("初始库存量：", self.initial_inventory),
            ("持有成本（每箱/周）：", self.holding_cost),
            ("缺货成本（每箱/周）：", self.backlog_cost),
            ("游戏总周数：", self.max_weeks),
        ]
        for text, var in entries:
            ttk.Label(config_frame, text=text, font=("Helvetica", 12)).pack(anchor='w', pady=8)
            ttk.Entry(config_frame, textvariable=var, width=15, font=("Helvetica", 12)).pack(anchor='w', padx=30)

        demand_frame = ttk.LabelFrame(config_frame, text="消费者需求手动设置（空格分隔数字）", padding=10)
        demand_frame.pack(fill='x', pady=20)

        self.demand_text = scrolledtext.ScrolledText(demand_frame, height=8, font=("Helvetica", 11))
        self.demand_text.pack(fill='x', padx=10)
        self.load_classic_demand()

        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="载入经典需求", command=self.load_classic_demand).pack(side='left', padx=10)
        ttk.Button(btn_frame, text="应用需求并重置游戏", command=self.apply_custom_demand).pack(side='left', padx=10)

        ttk.Button(config_frame, text="仅应用基本参数并重置", command=self.apply_basic_only).pack(pady=20)

    def load_classic_demand(self):
        classic = [4] * 4 + [8] * (self.max_weeks.get() - 4)
        self.demand_text.delete('1.0', tk.END)
        self.demand_text.insert(tk.END, ' '.join(map(str, classic)))

    def apply_custom_demand(self):
        try:
            text = self.demand_text.get('1.0', tk.END).strip()
            new_demand = [int(x) for x in text.split()]
            if len(new_demand) != self.max_weeks.get():
                messagebox.showerror("错误", f"必须输入 {self.max_weeks.get()} 个数字")
                return
            new_inv = max(0, self.initial_inventory.get())
            new_hold = max(0.0, self.holding_cost.get())
            new_back = max(0.0, self.backlog_cost.get())
            new_weeks = self.max_weeks.get()

            self.game = BeerGame(new_inv, new_hold, new_back, new_weeks, new_demand)
            self.reset_inputs()
            self.update_all()
            messagebox.showinfo("成功", "消费者需求已更新，游戏已重置！")
        except ValueError:
            messagebox.showerror("错误", "需求必须是整数，用空格分隔")

    def apply_basic_only(self):
        new_inv = max(0, self.initial_inventory.get())
        new_hold = max(0.0, self.holding_cost.get())
        new_back = max(0.0, self.backlog_cost.get())
        new_weeks = self.max_weeks.get()

        current_demand = self.game.customer_demand
        self.game = BeerGame(new_inv, new_hold, new_back, new_weeks, current_demand)
        self.reset_inputs()
        self.update_all()
        messagebox.showinfo("成功", "基本参数已更新，游戏已重置（需求保持不变）")

    def reset_inputs(self):
        for spin in self.order_spins.values():
            spin.delete(0, 'end')
            spin.insert(0, '4')
        if self.production_spin:
            self.production_spin.delete(0, 'end')
            self.production_spin.insert(0, '4')

    def create_role_frame(self, frame, role_zh):
        role_en = self.game.role_en[self.game.roles_zh.index(role_zh)]

        status_frame = ttk.LabelFrame(frame, text="当前状态", padding=15)
        status_frame.pack(fill='x', padx=30, pady=15)
        labels = ["库存", "缺货积压", "累计成本"]
        for i, txt in enumerate(labels):
            ttk.Label(status_frame, text=f"{txt}：", font=("Helvetica", 12)).grid(row=i, column=0, sticky='w', padx=20,
                                                                                 pady=10)
            var = tk.StringVar(value=str(self.game.initial_inventory) if txt == "库存" else "0.00")
            ttk.Label(status_frame, textvariable=var, font=("Helvetica", 14, "bold")).grid(row=i, column=1, sticky='w',
                                                                                           padx=10)
            self.status_vars[f"{role_en}_{txt}"] = var

        input_frame = ttk.LabelFrame(frame, text="本周决策", padding=15)
        input_frame.pack(fill='x', padx=30, pady=20)

        if role_en == 'manufacturer':
            ttk.Label(input_frame, text="本周生产量：", font=("Helvetica", 13, "bold")).pack(side='left', padx=30)
            spin = tk.Spinbox(input_frame, from_=0, to=500, increment=1, width=15, font=("Helvetica", 14))
            spin.pack(side='left', padx=20)
            spin.delete(0, 'end')
            spin.insert(0, '4')
            self.production_spin = spin
        else:
            ttk.Label(input_frame, text="本周订单量：", font=("Helvetica", 13, "bold")).pack(side='left', padx=30)
            spin = tk.Spinbox(input_frame, from_=0, to=500, increment=1, width=15, font=("Helvetica", 14))
            spin.pack(side='left', padx=20)
            spin.delete(0, 'end')
            spin.insert(0, '10' if role_en == 'retailer' else '4')  # 零售商默认10
            self.order_spins[role_en] = spin

    def create_overview_frame(self, frame):
        self.figure = plt.Figure(figsize=(12, 7), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=20, pady=20)

    def update_orders_and_production(self):
        for role_en in ['retailer', 'wholesaler', 'distributor']:
            try:
                amount = int(self.order_spins[role_en].get())
                self.game.place_order(role_en, max(0, amount))
            except:
                self.game.place_order(role_en, 4)

        try:
            prod = int(self.production_spin.get())
            self.game.set_production(prod)
        except:
            self.game.set_production(4)

    def update_all(self):
        for role_zh in self.game.roles_zh:
            role_en = self.game.role_en[self.game.roles_zh.index(role_zh)]
            self.status_vars[f"{role_en}_库存"].set(str(self.game.inventory[role_en]))
            self.status_vars[f"{role_en}_缺货积压"].set(str(self.game.backlog[role_en]))
            self.status_vars[f"{role_en}_累计成本"].set(f"{self.game.cumulative_cost[role_en]:.2f}")

        self.week_label.config(text=f"当前周次: {self.game.current_week + 1}/{self.game.max_weeks}")
        self.update_overview()
        self.root.update_idletasks()

    def update_overview(self):
        self.ax.clear()
        weeks = list(range(self.game.current_week + 1))
        self.ax.plot(weeks, self.game.customer_demand[:self.game.current_week + 1],
                     label="消费者需求", linewidth=6, color='black', linestyle='--')

        colors = ['red', 'orange', 'green']
        roles_to_plot = ['零售商', '批发商', '分销商']
        for i, role_zh in enumerate(reversed(roles_to_plot)):
            role_en = self.game.role_en[self.game.roles_zh.index(role_zh)]
            orders = self.game.orders_placed[role_en][:self.game.current_week + 1]
            self.ax.plot(weeks[:len(orders)], orders, label=f"{role_zh} 订单量", linewidth=3.5, color=colors[i])

        self.ax.set_title("牛鞭效应可视化 — 需求波动逐级放大", fontsize=20, fontweight='bold')
        self.ax.set_xlabel("周次", fontsize=14)
        self.ax.set_ylabel("订单量 (箱)", fontsize=14)
        self.ax.legend(fontsize=13, loc='upper left')
        self.ax.grid(True, alpha=0.4)
        self.figure.tight_layout()
        self.canvas.draw()

    def next_week(self):
        self.update_orders_and_production()
        if self.game.advance_week():
            self.update_all()
        else:
            total = sum(self.game.cumulative_cost.values())
            messagebox.showinfo("游戏结束", f"{self.game.max_weeks}周已完成！\n全链总成本：{total:.2f} 元")


if __name__ == "__main__":
    root = tk.Tk()
    app = BeerGameApp(root)
    root.mainloop()